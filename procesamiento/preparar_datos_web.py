# -*- coding: utf-8 -*-
"""
Prepara el archivo de datos que usa la página web (datos/listas.json).

Toma los archivos que ya generan los otros scripts y los junta en un solo
archivo liviano con todo lo necesario para el cruce:
  - sdn.csv y alt.csv          -> nombres principales y alias de OFAC
  - sdn_documentos.csv         -> documentos de OFAC (generado por extraer_documentos_sdn.py)
  - lista_onu.csv              -> nombres, alias y documentos de la ONU (generado por convertir_onu_a_csv.py)
  - lista_ue.csv               -> terroristas de la Unión Europea (generado por convertir_ue.py)
  - lista_bid.csv              -> sancionados del BID y otros bancos (generado por convertir_bid.py)

Orden para actualizar las listas:
    python descargar_listas.py
    python extraer_documentos_sdn.py
    python convertir_onu_a_csv.py
    python convertir_ue.py
    python convertir_bid.py
    python preparar_datos_web.py

Solo usa librerías que ya vienen con Python.
"""

import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

# El script siempre trabaja en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_SALIDA = os.path.join("..", "datos", "listas.json")

# Mínimos de seguridad: si una lista descargada trae muchos menos registros de
# lo normal, probablemente la descarga quedó dañada y no se publica.
MINIMO_REGISTROS_OFAC = 10_000
MINIMO_REGISTROS_ONU = 500
MINIMO_REGISTROS_UE = 10
MINIMO_REGISTROS_BID = 100

TIPOS_REGISTRO = {
    "individual": "persona natural",
    "vessel": "barco",
    "aircraft": "aeronave",
    "-0-": "persona juridica",
}


def limpiar(valor):
    """Quita espacios y convierte el "-0-" de OFAC en texto vacío."""
    valor = (valor or "").strip()
    return "" if valor == "-0-" else valor


def limpiar_programa(programa):
    """'SDGT] [IRGC' -> 'SDGT | IRGC'"""
    partes = [p.strip() for p in re.split(r"\]\s*\[", limpiar(programa)) if p.strip()]
    return " | ".join(partes)


def limpiar_documento(doc):
    """Solo letras y números, en mayúscula y sin ceros a la izquierda.
    Debe hacer exactamente lo mismo que la función limpiarDocumento de motor.js."""
    doc = re.sub(r"[^A-Za-z0-9]", "", doc or "").upper()
    return doc.lstrip("0")


def leer_ofac(nombre_archivo):
    """Lee un CSV de OFAC (sin encabezados) y descarta la fila final de control."""
    with open(nombre_archivo, encoding="latin-1", newline="") as archivo:
        return [fila for fila in csv.reader(archivo) if len(fila) > 1 and fila[0].strip().isdigit()]


def leer_punto_y_coma(nombre_archivo):
    with open(nombre_archivo, encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo, delimiter=";"))


registros = []     # [fuente, id, nombre principal, tipo de registro, programa]
posicion = {}      # (fuente, id) -> posición en registros
nombres = []       # [posición del registro, nombre, tipo de nombre]
documentos = []    # [posición del registro, documento limpio, tipo de documento, país]

# ------------------------------------------------------------
# OFAC
# ------------------------------------------------------------
for fila in leer_ofac("sdn.csv"):
    id_ofac = fila[0].strip()
    posicion[("OFAC", id_ofac)] = len(registros)
    tipo = TIPOS_REGISTRO.get(fila[2].strip(), fila[2].strip())
    registros.append(["OFAC", id_ofac, limpiar(fila[1]), tipo, limpiar_programa(fila[3])])
    nombres.append([posicion[("OFAC", id_ofac)], limpiar(fila[1]), "PRINCIPAL"])

total_ofac = len(registros)

for fila in leer_ofac("alt.csv"):
    clave = ("OFAC", fila[0].strip())
    if clave in posicion and limpiar(fila[3]):
        nombres.append([posicion[clave], limpiar(fila[3]), f"ALIAS ({limpiar(fila[2])})"])

for fila in leer_punto_y_coma("sdn_documentos.csv"):
    clave = ("OFAC", fila["id_ofac"].strip())
    doc = limpiar_documento(fila["numero_normalizado"])
    if clave in posicion and doc:
        documentos.append([posicion[clave], doc, fila["tipo_documento"], fila["pais_documento"]])

# ------------------------------------------------------------
# ONU, Unión Europea y BID
# Las tres listas vienen en el mismo formato (lista_onu.csv, lista_ue.csv,
# lista_bid.csv), así que se cargan con la misma función.
# ------------------------------------------------------------
def cargar_lista(nombre_archivo):
    """Agrega una lista en formato lista_*.csv y devuelve (registros agregados, fecha de la lista)."""
    filas = leer_punto_y_coma(nombre_archivo)
    antes = len(registros)
    for fila in filas:
        clave = (fila["fuente"], fila["id_original"])
        if fila["tipo_nombre"] == "PRINCIPAL" and clave not in posicion:
            posicion[clave] = len(registros)
            registros.append([fila["fuente"], fila["id_original"], fila["nombre"], fila["tipo"],
                              fila["programa_o_regimen"]])
            tipos_doc = (fila["tipo_documento"] or "").split(" | ")
            for i, numero in enumerate((fila["numero_documento"] or "").split(" | ")):
                doc = limpiar_documento(numero)
                if doc:
                    tipo_doc = tipos_doc[i] if i < len(tipos_doc) else ""
                    documentos.append([posicion[clave], doc, tipo_doc, fila["pais"]])
    for fila in filas:
        clave = (fila["fuente"], fila["id_original"])
        if clave in posicion and fila["nombre"]:
            nombres.append([posicion[clave], fila["nombre"], fila["tipo_nombre"]])
    fecha = filas[0]["fecha_descarga"] if filas else ""
    return len(registros) - antes, fecha


total_onu, fecha_onu = cargar_lista("lista_onu.csv")
total_ue, fecha_ue = cargar_lista("lista_ue.csv")
total_bid, fecha_bid = cargar_lista("lista_bid.csv")

# ------------------------------------------------------------
# Revisión de seguridad y guardado
# ------------------------------------------------------------
if (total_ofac < MINIMO_REGISTROS_OFAC or total_onu < MINIMO_REGISTROS_ONU
        or total_ue < MINIMO_REGISTROS_UE or total_bid < MINIMO_REGISTROS_BID):
    sys.exit(f"ERROR: las listas parecen incompletas (OFAC: {total_ofac}, ONU: {total_onu}, "
             f"UE: {total_ue}, BID: {total_bid}). "
             "No se actualizó la página.")

hora_colombia = datetime.now(timezone(timedelta(hours=-5)))
datos = {
    "meta": {
        "fecha_actualizacion": hora_colombia.strftime("%Y-%m-%d"),
        "fecha_lista_onu": fecha_onu,
        "registros_ofac": total_ofac,
        "registros_onu": total_onu,
        "fecha_lista_ue": fecha_ue,
        "registros_ue": total_ue,
        "fecha_lista_bid": fecha_bid,
        "registros_bid": total_bid,
    },
    "registros": registros,
    "nombres": nombres,
    "documentos": documentos,
}

os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)
with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as archivo:
    json.dump(datos, archivo, ensure_ascii=False, separators=(",", ":"))

print(f"Listo. Archivo generado: {ARCHIVO_SALIDA}")
print(f"  Registros OFAC: {total_ofac:,} | ONU: {total_onu:,} | UE: {total_ue:,} | BID: {total_bid:,}")
print(f"  Nombres (con alias): {len(nombres):,} | Documentos: {len(documentos):,}")
