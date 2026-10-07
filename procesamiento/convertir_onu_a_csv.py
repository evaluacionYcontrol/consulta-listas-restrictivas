# -*- coding: utf-8 -*-
"""
Convierte la Lista Consolidada del Consejo de Seguridad de la ONU (XML)
a un archivo CSV listo para cruzar contra la base de suministros.

Cada fila del CSV es UNA variante de nombre:
  - una fila con el nombre principal
  - una fila adicional por cada alias
Así, cualquier forma en que aparezca el nombre puede generar coincidencia.

Solo usa librerías que ya vienen con Python (no hay que instalar nada).
"""

import csv
import os
import unicodedata
import xml.etree.ElementTree as ET

# El script siempre busca los archivos en la carpeta donde está guardado
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------
# 1. Configuración: nombres de los archivos
#    (el XML debe estar en la misma carpeta que este script)
# ------------------------------------------------------------
ARCHIVO_XML = "consolidatedLegacyByPRN.xml"
ARCHIVO_CSV = "lista_onu.csv"


# ------------------------------------------------------------
# 2. Funciones de apoyo
# ------------------------------------------------------------
def texto(elemento, etiqueta):
    """Devuelve el texto de una etiqueta hija, limpio. Si no existe, devuelve ''."""
    hijo = elemento.find(etiqueta)
    if hijo is None or hijo.text is None:
        return ""
    # Quita saltos de línea y espacios dobles
    return " ".join(hijo.text.split())


def normalizar(nombre):
    """Pasa el nombre a MAYÚSCULAS, sin tildes, sin signos y sin espacios dobles.
    Esta es la columna que se usará después para comparar con suministros."""
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = "".join(c if c.isalnum() else " " for c in nombre)
    return " ".join(nombre.upper().split())


def valores(elemento, etiqueta):
    """Junta todos los <VALUE> dentro de una etiqueta (ej. varias nacionalidades)."""
    lista = []
    for bloque in elemento.findall(etiqueta):
        for v in bloque.findall("VALUE"):
            if v.text and v.text.strip():
                lista.append(" ".join(v.text.split()))
    return " | ".join(lista)


# ------------------------------------------------------------
# 3. Leer el XML
# ------------------------------------------------------------
arbol = ET.parse(ARCHIVO_XML)
raiz = arbol.getroot()

# Fecha en que la ONU generó el archivo (sirve como evidencia de la versión)
fecha_lista = raiz.get("dateGenerated", "")[:10]

filas = []

# ------------------------------------------------------------
# 4. Personas (INDIVIDUALS)
# ------------------------------------------------------------
for persona in raiz.iter("INDIVIDUAL"):
    # Nombre completo = unir primer, segundo, tercer y cuarto nombre
    partes = [texto(persona, e) for e in ["FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME"]]
    nombre_principal = " ".join(p for p in partes if p)

    # Documentos (pasaportes, identificaciones): puede haber varios
    numeros, tipos = [], []
    for doc in persona.findall("INDIVIDUAL_DOCUMENT"):
        numero = texto(doc, "NUMBER")
        if numero:
            numeros.append(numero)
            tipos.append(texto(doc, "TYPE_OF_DOCUMENT"))

    # Fechas de nacimiento: pueden ser fecha exacta, solo año o un rango
    fechas = []
    for fn in persona.findall("INDIVIDUAL_DATE_OF_BIRTH"):
        if texto(fn, "DATE"):
            fechas.append(texto(fn, "DATE"))
        elif texto(fn, "YEAR"):
            fechas.append(texto(fn, "YEAR"))
        elif texto(fn, "FROM_YEAR"):
            fechas.append(texto(fn, "FROM_YEAR") + "-" + texto(fn, "TO_YEAR"))

    # País: se usa la nacionalidad; si no hay, el país de la dirección
    pais = valores(persona, "NATIONALITY")
    if not pais:
        paises = [texto(d, "COUNTRY") for d in persona.findall("INDIVIDUAL_ADDRESS")]
        pais = " | ".join(p for p in paises if p)

    # Datos que se repiten igual en todas las filas de esta persona
    datos_comunes = {
        "fuente": "ONU",
        "id_original": texto(persona, "REFERENCE_NUMBER"),
        "tipo": "persona natural",
        "numero_documento": " | ".join(numeros),
        "tipo_documento": " | ".join(tipos),
        "pais": pais,
        "fecha_nacimiento": " | ".join(fechas),
        "programa_o_regimen": texto(persona, "UN_LIST_TYPE"),
        "fecha_inclusion": texto(persona, "LISTED_ON"),
        "fecha_descarga": fecha_lista,
    }

    # Fila del nombre principal
    filas.append({**datos_comunes, "nombre": nombre_principal,
                  "nombre_normalizado": normalizar(nombre_principal),
                  "tipo_nombre": "PRINCIPAL", "calidad_alias": ""})

    # Una fila por cada alias
    for alias in persona.findall("INDIVIDUAL_ALIAS"):
        nombre_alias = texto(alias, "ALIAS_NAME")
        if nombre_alias:
            filas.append({**datos_comunes, "nombre": nombre_alias,
                          "nombre_normalizado": normalizar(nombre_alias),
                          "tipo_nombre": "ALIAS", "calidad_alias": texto(alias, "QUALITY")})

# ------------------------------------------------------------
# 5. Entidades (ENTITIES): empresas, grupos, organizaciones
# ------------------------------------------------------------
for entidad in raiz.iter("ENTITY"):
    nombre_principal = texto(entidad, "FIRST_NAME")

    paises = [texto(d, "COUNTRY") for d in entidad.findall("ENTITY_ADDRESS")]
    pais = " | ".join(p for p in paises if p)

    datos_comunes = {
        "fuente": "ONU",
        "id_original": texto(entidad, "REFERENCE_NUMBER"),
        "tipo": "persona juridica",
        "numero_documento": "",      # la ONU no trae NIT ni documentos de entidades
        "tipo_documento": "",
        "pais": pais,
        "fecha_nacimiento": "",
        "programa_o_regimen": texto(entidad, "UN_LIST_TYPE"),
        "fecha_inclusion": texto(entidad, "LISTED_ON"),
        "fecha_descarga": fecha_lista,
    }

    filas.append({**datos_comunes, "nombre": nombre_principal,
                  "nombre_normalizado": normalizar(nombre_principal),
                  "tipo_nombre": "PRINCIPAL", "calidad_alias": ""})

    for alias in entidad.findall("ENTITY_ALIAS"):
        nombre_alias = texto(alias, "ALIAS_NAME")
        if nombre_alias:
            filas.append({**datos_comunes, "nombre": nombre_alias,
                          "nombre_normalizado": normalizar(nombre_alias),
                          "tipo_nombre": "ALIAS", "calidad_alias": texto(alias, "QUALITY")})

# ------------------------------------------------------------
# 6. Guardar el CSV
#    - separador ";" para que Excel en configuración Colombia lo abra bien
#    - utf-8-sig para que las tildes y caracteres especiales se vean bien
# ------------------------------------------------------------
columnas = ["fuente", "id_original", "tipo", "tipo_nombre", "calidad_alias",
            "nombre", "nombre_normalizado", "numero_documento", "tipo_documento",
            "pais", "fecha_nacimiento", "programa_o_regimen",
            "fecha_inclusion", "fecha_descarga"]

with open(ARCHIVO_CSV, "w", newline="", encoding="utf-8-sig") as f:
    escritor = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
    escritor.writeheader()
    escritor.writerows(filas)

# Resumen en pantalla
personas = len(list(raiz.iter("INDIVIDUAL")))
entidades = len(list(raiz.iter("ENTITY")))
print("Listo. Archivo generado:", ARCHIVO_CSV)
print("Versión de la lista (fecha ONU):", fecha_lista)
print("Personas:", personas, "| Entidades:", entidades, "| Filas totales (con alias):", len(filas))
