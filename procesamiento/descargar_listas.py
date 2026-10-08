# -*- coding: utf-8 -*-
"""
Descarga las versiones más recientes de las listas restrictivas:
  - OFAC (Lista SDN / "Lista Clinton"): sdn.csv, alt.csv, add.csv, sdn_comments.csv
  - ONU (Lista Consolidada del Consejo de Seguridad): consolidatedLegacyByPRN.xml
  - Unión Europea (lista consolidada de sanciones financieras): ue_fuente.csv
  - BID (firmas y personas sancionadas, incluye inhabilitaciones cruzadas
    del Banco Mundial y otros bancos multilaterales): bid_fuente.csv

Los archivos se guardan en esta misma carpeta, con los nombres que esperan
extraer_documentos_sdn.py y convertir_onu_a_csv.py.

Si alguna descarga falla, el script termina con error y NO se actualiza nada:
la página sigue funcionando con la versión anterior de las listas.

Solo usa librerías que ya vienen con Python.
"""

import csv
import io
import json
import os
import sys
import urllib.request

# El script siempre trabaja en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Para cada archivo: nombre con el que se guarda, tamaño mínimo esperado (bytes)
# y direcciones de descarga (se prueba la primera; si falla, la siguiente).
ARCHIVOS = [
    ("sdn.csv", 1_000_000, [
        "https://sanctionslistservice.ofac.treas.gov/api/download/SDN.CSV",
        "https://www.treasury.gov/ofac/downloads/sdn.csv",
    ]),
    ("alt.csv", 300_000, [
        "https://sanctionslistservice.ofac.treas.gov/api/download/ALT.CSV",
        "https://www.treasury.gov/ofac/downloads/alt.csv",
    ]),
    ("add.csv", 300_000, [
        "https://sanctionslistservice.ofac.treas.gov/api/download/ADD.CSV",
        "https://www.treasury.gov/ofac/downloads/add.csv",
    ]),
    ("sdn_comments.csv", 1_000, [
        "https://sanctionslistservice.ofac.treas.gov/api/download/SDN_COMMENTS.CSV",
        "https://www.treasury.gov/ofac/downloads/sdn_comments.csv",
    ]),
    ("consolidatedLegacyByPRN.xml", 500_000, [
        "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    ]),
    # Enlace público oficial de la Comisión Europea (el "token" es el mismo para todos)
    ("ue_fuente.csv", 1_000_000, [
        "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
    ]),
]

# Lista del BID en su portal de datos abiertos (data.iadb.org)
BID_RECURSO = "cd0bd9ac-18c6-44bc-8592-9be468c2efd9"
BID_TAMANO_MINIMO = 20_000


def descargar(url):
    """Descarga una dirección y devuelve su contenido en bytes."""
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (actualizacion-listas)"})
    with urllib.request.urlopen(pedido, timeout=120) as respuesta:
        return respuesta.read()


def descargar_bid():
    """Descarga la lista del BID. Primero pregunta al portal cuál es el archivo
    vigente; si eso falla, arma el CSV a partir de la consulta de datos del portal."""
    try:
        info = json.loads(descargar("https://data.iadb.org/api/3/action/resource_show?id=" + BID_RECURSO))
        contenido = descargar(info["result"]["url"])
        if len(contenido) >= BID_TAMANO_MINIMO and b"Title" in contenido[:500]:
            print("Descargado bid_fuente.csv desde el archivo del portal del BID")
            return contenido
    except Exception as error:
        print(f"  No se pudo descargar el archivo del BID: {error}")
    try:
        datos = json.loads(descargar("https://data.iadb.org/api/action/datastore_search?resource_id="
                                     + BID_RECURSO + "&limit=20000"))
        campos = [c["id"] for c in datos["result"]["fields"] if c["id"] != "_id"]
        salida = io.StringIO()
        escritor = csv.DictWriter(salida, fieldnames=campos, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(datos["result"]["records"])
        contenido = salida.getvalue().encode("utf-8-sig")
        if len(contenido) >= BID_TAMANO_MINIMO:
            print("Descargado bid_fuente.csv desde la consulta de datos del BID")
            return contenido
    except Exception as error:
        print(f"  No se pudo consultar los datos del BID: {error}")
    return None


# Primero se descarga todo en memoria; solo si TODO salió bien se guardan los archivos.
descargados = {}
for nombre, tamano_minimo, direcciones in ARCHIVOS:
    for url in direcciones:
        try:
            contenido = descargar(url)
        except Exception as error:
            print(f"  No se pudo descargar {url}: {error}")
            continue
        if len(contenido) < tamano_minimo:
            print(f"  {url} respondió, pero el archivo es demasiado pequeño ({len(contenido)} bytes)")
            continue
        descargados[nombre] = contenido
        print(f"Descargado {nombre} ({len(contenido):,} bytes) desde {url}")
        break
    else:
        sys.exit(f"ERROR: no se pudo descargar {nombre}. No se actualizó ninguna lista.")

contenido_bid = descargar_bid()
if contenido_bid is None:
    sys.exit("ERROR: no se pudo descargar la lista del BID. No se actualizó ninguna lista.")
descargados["bid_fuente.csv"] = contenido_bid

for nombre, contenido in descargados.items():
    with open(nombre, "wb") as archivo:
        archivo.write(contenido)

print("Listo. Todas las listas se descargaron correctamente.")
