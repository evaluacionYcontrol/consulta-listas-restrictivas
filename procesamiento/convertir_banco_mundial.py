# -*- coding: utf-8 -*-
"""
Convierte la lista de firmas y personas inhabilitadas del Banco Mundial
("World Bank Listing of Ineligible Firms and Individuals") al mismo formato
que lista_onu.csv, para que la herramienta la pueda usar.

Cómo obtener el archivo de entrada:
  1. Entrar a https://www.worldbank.org/en/projects-operations/procurement/debarred-firms
  2. En la tabla "Debarred Firms and Individuals", usar la opción de exportar a Excel.
  3. Guardar el archivo descargado en esta carpeta con el nombre bm_fuente.xlsx
     (reemplazando el anterior).

Entrada:  bm_fuente.xlsx
Salida:   lista_bm.csv

Solo se incluyen las inhabilitaciones vigentes (fecha final igual o posterior a hoy;
el Banco Mundial usa el año 2999 para las inhabilitaciones indefinidas).
Solo usa librerías que vienen con Python (el Excel se lee directamente, sin pandas).
"""

import csv
import os
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

# El script siempre trabaja en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ARCHIVO_ENTRADA = "bm_fuente.xlsx"
ARCHIVO_SALIDA = "lista_bm.csv"

# Tratamientos que se quitan del nombre para poder compararlo ("MR. ABDUR RASHID" -> "ABDUR RASHID")
TRATAMIENTOS = re.compile(r"^(?:MR|MRS|MS|MISS|DR|PROF|ENG|ENGR|SR|SRA)\.?\s+", re.IGNORECASE)
# Nombres alternos dentro de la columna de información adicional: "(AKA ...)", "(F/K/A ...)"
ALIAS = re.compile(r"\((?:AKA|A/K/A|F/K/A|FKA|D/B/A|DBA|N/K/A|FORMERLY KNOWN AS|ALSO KNOWN AS)[:\s]+([^)]*)\)", re.IGNORECASE)
# Número de registro de la empresa: "(Reg. No: 2015/397741/07)"
REGISTRO = re.compile(r"Reg\.?\s*No\.?\s*:?\s*([^)]+)\)", re.IGNORECASE)

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def leer_excel(ruta):
    """Lee la primera hoja de un .xlsx y devuelve una lista de filas (listas de texto)."""
    with zipfile.ZipFile(ruta) as libro:
        compartidos = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz = ET.fromstring(libro.read("xl/sharedStrings.xml"))
            for si in raiz.findall("m:si", NS):
                compartidos.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        hojas = sorted(n for n in libro.namelist() if n.startswith("xl/worksheets/sheet"))
        raiz = ET.fromstring(libro.read(hojas[0]))
    filas = []
    for fila in raiz.iter("{%s}row" % NS["m"]):
        valores = {}
        for celda in fila.findall("m:c", NS):
            columna = re.match(r"[A-Z]+", celda.get("r")).group()
            indice = 0
            for letra in columna:
                indice = indice * 26 + (ord(letra) - 64)
            tipo = celda.get("t")
            if tipo == "inlineStr":
                texto = "".join(t.text or "" for t in celda.iter("{%s}t" % NS["m"]))
            else:
                v = celda.find("m:v", NS)
                texto = "" if v is None else (v.text or "")
                if tipo == "s" and texto:
                    texto = compartidos[int(texto)]
            valores[indice - 1] = texto.strip()
        if valores:
            filas.append([valores.get(i, "") for i in range(max(valores) + 1)])
    return filas


def a_fecha(texto):
    """Convierte la fecha del Excel (texto aaaa-mm-dd o número de serie de Excel) a date."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto[:10]).date()
    except ValueError:
        pass
    try:
        return date(1899, 12, 30) + timedelta(days=int(float(texto)))
    except ValueError:
        return None


def normalizar(nombre):
    """MAYÚSCULAS, sin tildes ni signos (igual que en convertir_onu_a_csv.py)."""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = "".join(c if c.isalnum() else " " for c in nombre)
    return " ".join(nombre.upper().split())


filas = leer_excel(ARCHIVO_ENTRADA)

# Fecha de descarga: la primera fila dice "Downloaded on: dd/mm/aaaa hh:mm"
fecha_lista = ""
coincidencia = re.search(r"(\d{2})/(\d{2})/(\d{4})", " ".join(filas[0]) if filas else "")
if coincidencia:
    fecha_lista = f"{coincidencia.group(3)}-{coincidencia.group(2)}-{coincidencia.group(1)}"

# Buscar la fila de encabezados ("Firm Name"); los datos empiezan dos filas después
inicio = next(i for i, f in enumerate(filas) if f and f[0].strip().lower() == "firm name") + 2

hoy = datetime.now(timezone(timedelta(hours=-5))).date()
salida = []
vigentes = 0
for numero, f in enumerate(filas[inicio:], start=1):
    f = f + [""] * (7 - len(f))
    nombre, datos, direccion, pais, desde, hasta, fundamento = f[:7]
    if not nombre:
        continue
    fin = a_fecha(hasta)
    if fin and fin < hoy:
        continue                                  # inhabilitación terminada
    vigentes += 1

    persona = bool(TRATAMIENTOS.match(nombre))
    nombre_limpio = TRATAMIENTOS.sub("", nombre).strip()
    alias = [a.strip() for a in ALIAS.findall(datos) if a.strip()]
    registro = REGISTRO.search(datos)
    hasta_texto = "indefinida" if fin and fin.year >= 2999 else (fin.isoformat() if fin else "")
    programa = " | ".join(p for p in ["Banco Mundial", fundamento.strip(),
                                       "inhabilitado hasta: " + hasta_texto if hasta_texto else ""] if p)

    datos_comunes = {
        "fuente": "BM",
        "id_original": f"BM-{numero:04d}",
        "tipo": "persona natural" if persona else "firma o persona",
        "calidad_alias": "",
        "numero_documento": registro.group(1).strip() if registro else "",
        "tipo_documento": "registro mercantil" if registro else "",
        "pais": pais.strip(),
        "fecha_nacimiento": "",
        "programa_o_regimen": programa,
        "fecha_inclusion": a_fecha(desde).isoformat() if a_fecha(desde) else "",
        "fecha_descarga": fecha_lista,
    }
    for posicion, n in enumerate([nombre_limpio] + alias):
        salida.append({**datos_comunes, "nombre": n, "nombre_normalizado": normalizar(n),
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
print(f"Versión de la lista del Banco Mundial: {fecha_lista} | Inhabilitaciones vigentes: {vigentes} | Filas con alias: {len(salida)}")
