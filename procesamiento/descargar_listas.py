# -*- coding: utf-8 -*-
"""
Descarga las versiones más recientes de las listas restrictivas:
  - OFAC (Lista SDN / "Lista Clinton"): sdn.csv, alt.csv, add.csv, sdn_comments.csv
  - ONU (Lista Consolidada del Consejo de Seguridad): consolidatedLegacyByPRN.xml

Los archivos se guardan en esta misma carpeta, con los nombres que esperan
extraer_documentos_sdn.py y convertir_onu_a_csv.py.

Si alguna descarga falla, el script termina con error y NO se actualiza nada:
la página sigue funcionando con la versión anterior de las listas.

Solo usa librerías que ya vienen con Python.
"""

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
]


def descargar(url):
    """Descarga una dirección y devuelve su contenido en bytes."""
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (actualizacion-listas)"})
    with urllib.request.urlopen(pedido, timeout=120) as respuesta:
        return respuesta.read()


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

for nombre, contenido in descargados.items():
    with open(nombre, "wb") as archivo:
        archivo.write(contenido)

print("Listo. Todas las listas se descargaron correctamente.")
