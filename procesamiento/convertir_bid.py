# -*- coding: utf-8 -*-
"""
Convierte la lista de firmas y personas sancionadas del BID (datos abiertos)
al mismo formato que lista_onu.csv, para que la página la pueda usar.

La lista del BID incluye también las inhabilitaciones cruzadas del Banco Mundial,
el Banco Asiático de Desarrollo, el Banco Africano de Desarrollo y el BERD.

Entrada:  bid_fuente.csv  (descargado por descargar_listas.py)
Salida:   lista_bid.csv

Solo se incluyen las sanciones VIGENTES: las que dicen "Ongoing" o cuya fecha
de finalización todavía no ha pasado. Solo usa librerías que vienen con Python.
"""

import csv
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

# El script siempre trabaja en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_ENTRADA = "bid_fuente.csv"
ARCHIVO_SALIDA = "lista_bid.csv"

# Traducciones al español
FUENTES = {
    "IDB": "BID",
    "WBG cross debarment": "Banco Mundial (inhabilitación cruzada)",
    "ADB cross debarment": "Banco Asiático de Desarrollo (inhabilitación cruzada)",
    "AfDB cross debarment": "Banco Africano de Desarrollo (inhabilitación cruzada)",
    "EBRD cross debarment": "BERD (inhabilitación cruzada)",
}
PRACTICAS = {
    "Fraud": "Fraude", "Corruption": "Corrupción", "Collusion": "Colusión",
    "Coercion": "Coerción", "Obstruction": "Obstrucción", "Extortion": "Extorsión",
}
TIPOS = {"Individual": "persona natural", "Firm": "persona juridica"}

# Expresiones que separan un nombre de sus otros nombres dentro de la misma celda
SEPARADOR_ALIAS = re.compile(r",?\s*\(?\b(?:f/k/a|a/k/a|d/b/a|n/k/a|formerly known as|also known as)\b\s*", re.IGNORECASE)


def normalizar(nombre):
    """MAYÚSCULAS, sin tildes ni signos (igual que en convertir_onu_a_csv.py)."""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = "".join(c if c.isalnum() else " " for c in nombre)
    return " ".join(nombre.upper().split())


def traducir_practicas(texto):
    partes = [p.strip() for p in (texto or "").split(",") if p.strip()]
    return ", ".join(PRACTICAS.get(p, p) for p in partes)


hoy = datetime.now(timezone(timedelta(hours=-5))).date()

with open(ARCHIVO_ENTRADA, encoding="utf-8-sig", newline="") as archivo:
    filas = list(csv.DictReader(archivo))

salida = []
vigentes = 0
for numero, fila in enumerate(filas, start=1):
    fin = (fila.get("To") or "").strip()
    if fin and fin.lower() != "ongoing":
        try:
            if datetime.fromisoformat(fin[:10]).date() < hoy:
                continue                      # sanción ya terminada
        except ValueError:
            pass                              # fecha rara: se deja por precaución
    vigentes += 1

    nombres = [n.strip(" ,()") for n in SEPARADOR_ALIAS.split(fila["Title"] or "") if n.strip(" ,()")]
    if not nombres:
        continue

    hasta = "indefinida" if not fin or fin.lower() == "ongoing" else fin[:10]
    programa = " | ".join(p for p in [
        FUENTES.get((fila.get("Source") or "").strip(), (fila.get("Source") or "").strip()),
        traducir_practicas(fila.get("Prohibited Practice")),
        "inhabilitado hasta: " + hasta,
    ] if p)
    pais = (fila.get("Nationality") or fila.get("Country") or "").strip()

    datos_comunes = {
        "fuente": "BID",
        "id_original": f"BID-{numero:04d}",
        "tipo": TIPOS.get((fila.get("Entity") or "").strip(), "persona juridica"),
        "calidad_alias": "",
        "numero_documento": "",               # el BID no publica documentos de identidad
        "tipo_documento": "",
        "pais": pais,
        "fecha_nacimiento": "",
        "programa_o_regimen": programa,
        "fecha_inclusion": (fila.get("From") or "")[:10],
        "fecha_descarga": hoy.isoformat(),
    }
    for posicion, nombre in enumerate(nombres):
        salida.append({**datos_comunes, "nombre": nombre, "nombre_normalizado": normalizar(nombre),
                       "tipo_nombre": "PRINCIPAL" if posicion == 0 else "ALIAS"})

columnas = ["fuente", "id_original", "tipo", "tipo_nombre", "calidad_alias",
            "nombre", "nombre_normalizado", "numero_documento", "tipo_documento",
            "pais", "fecha_nacimiento", "programa_o_regimen",
            "fecha_inclusion", "fecha_descarga"]
with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8-sig") as archivo:
    escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";")
    escritor.writeheader()
    escritor.writerows(salida)

print("Listo. Archivo generado:", ARCHIVO_SALIDA)
print(f"Registros en el archivo del BID: {len(filas)} | Sanciones vigentes: {vigentes} | Filas con alias: {len(salida)}")
