# -*- coding: utf-8 -*-
"""
Extrae de la lista consolidada de sanciones financieras de la Unión Europea
las personas y organizaciones catalogadas como terroristas, y las deja en el
mismo formato que lista_onu.csv para que la página las pueda usar.

Entrada:  ue_fuente.csv  (descargado por descargar_listas.py)
Salida:   lista_ue.csv

Programas incluidos (se pueden cambiar en PROGRAMAS_UE):
  TERR -> Lista de terroristas de la UE (Posición Común 2001/931/PESC)
  EUAQ -> Régimen propio de la UE contra el ISIL (Daesh) y Al-Qaida
Para incluir TODAS las sanciones financieras de la UE, deje PROGRAMAS_UE vacío: set()

Solo usa librerías que vienen con Python.
"""

import csv
import os
import unicodedata
from collections import OrderedDict

# El script siempre trabaja en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_ENTRADA = "ue_fuente.csv"
ARCHIVO_SALIDA = "lista_ue.csv"

PROGRAMAS_UE = {"TERR", "EUAQ"}
NOMBRES_PROGRAMA = {
    "TERR": "Lista de terroristas de la UE (Posición Común 2001/931/PESC)",
    "EUAQ": "UE: ISIL (Daesh) y Al-Qaida",
}
TIPOS = {"P": "persona natural", "E": "persona juridica"}

# El archivo de la UE trae columnas muy largas; se sube el límite por precaución
csv.field_size_limit(10_000_000)


def normalizar(nombre):
    """MAYÚSCULAS, sin tildes ni signos (igual que en convertir_onu_a_csv.py)."""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = "".join(c if c.isalnum() else " " for c in nombre)
    return " ".join(nombre.upper().split())


def agregar(lista, valor):
    """Agrega un valor a la lista solo si no está vacío ni repetido."""
    valor = (valor or "").strip()
    if valor and valor.upper() != "UNKNOWN" and valor not in lista:
        lista.append(valor)


# El archivo trae una fila por cada combinación de nombre, dirección, documento, etc.
# Aquí se agrupan todas las filas de cada sancionado.
registros = OrderedDict()
fecha_lista = ""
with open(ARCHIVO_ENTRADA, encoding="utf-8-sig", newline="") as archivo:
    for fila in csv.DictReader(archivo, delimiter=";"):
        fecha_lista = fecha_lista or fila.get("fileGenerationDate", "")
        programa = (fila.get("Entity_Regulation_Programme") or "").strip()
        if PROGRAMAS_UE and programa not in PROGRAMAS_UE:
            continue
        id_ue = fila["Entity_LogicalId"]
        r = registros.setdefault(id_ue, {
            "tipo": TIPOS.get(fila.get("Entity_SubjectType"), "persona juridica"),
            "programa": NOMBRES_PROGRAMA.get(programa, "UE: " + programa),
            "referencia": (fila.get("Entity_EU_ReferenceNumber") or "").strip(),
            "fecha_inclusion": (fila.get("Entity_DesignationDate") or "").strip(),
            "nombres": [], "documentos": [], "paises": [], "nacimientos": [],
        })
        agregar(r["nombres"], fila.get("NameAlias_WholeName"))
        # El número a veces trae notas entre paréntesis: "488555 (passport-National passport)"
        numero = (fila.get("Identification_Number") or "").split("(")[0].strip()
        if numero:
            documento = (numero, (fila.get("Identification_TypeDescription") or "").strip(),
                         (fila.get("Identification_CountryDescription") or "").strip())
            if documento not in r["documentos"]:
                r["documentos"].append(documento)
        agregar(r["paises"], fila.get("Citizenship_CountryDescription"))
        agregar(r["paises"], fila.get("Address_CountryDescription"))
        agregar(r["nacimientos"], fila.get("BirthDate_BirthDate") or fila.get("BirthDate_Year"))

# Fecha de la lista: la UE la escribe como dd/mm/aaaa
partes = fecha_lista.split("/")
fecha_iso = f"{partes[2]}-{partes[1]}-{partes[0]}" if len(partes) == 3 else fecha_lista

salida = []
for id_ue, r in registros.items():
    if not r["nombres"]:
        continue
    programa = r["programa"] + (f" | ref. {r['referencia']}" if r["referencia"] else "")
    datos_comunes = {
        "fuente": "UE",
        "id_original": "UE-" + id_ue,
        "tipo": r["tipo"],
        "calidad_alias": "",
        "numero_documento": " | ".join(d[0] for d in r["documentos"]),
        "tipo_documento": " | ".join(" ".join(p for p in d[1:] if p) for d in r["documentos"]),
        "pais": " | ".join(r["paises"]),
        "fecha_nacimiento": " | ".join(r["nacimientos"]),
        "programa_o_regimen": programa,
        "fecha_inclusion": r["fecha_inclusion"],
        "fecha_descarga": fecha_iso,
    }
    for posicion, nombre in enumerate(r["nombres"]):
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
print(f"Versión de la lista UE: {fecha_iso} | Sancionados incluidos: {len(registros)} | Filas con alias: {len(salida)}")
