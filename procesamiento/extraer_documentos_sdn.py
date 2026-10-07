# -*- coding: utf-8 -*-
"""
Organiza la lista SDN de OFAC ("Lista Clinton") y extrae los documentos de
identidad que vienen escritos dentro del campo "remarks" (observaciones).

Entrada (en esta misma carpeta):
    sdn.csv           -> lista principal
    sdn_comments.csv  -> continuación del campo remarks cuando es muy largo
    add.csv           -> direcciones

Salida:
    sdn_documentos.csv -> una fila por documento (o una fila vacía si el
                          registro no tiene documentos)

Cómo ejecutarlo (desde la terminal, dentro de la carpeta del proyecto):
    python extraer_documentos_sdn.py
"""

import csv          # módulo estándar de Python para leer y escribir archivos CSV
import re           # módulo de "expresiones regulares" para buscar patrones en texto
from collections import Counter   # sirve para contar cosas fácilmente
from pathlib import Path          # sirve para manejar rutas de archivos

# ---------------------------------------------------------------------------
# 1. RUTAS DE LOS ARCHIVOS
# ---------------------------------------------------------------------------
# CARPETA es la carpeta donde está guardado este script.
# Así el script solo lee y escribe dentro de esa carpeta.
CARPETA = Path(__file__).resolve().parent

ARCHIVO_SDN = CARPETA / "sdn.csv"
ARCHIVO_COMENTARIOS = CARPETA / "sdn_comments.csv"
ARCHIVO_DIRECCIONES = CARPETA / "add.csv"
ARCHIVO_SALIDA = CARPETA / "sdn_documentos.csv"

# OFAC usa "-0-" para indicar un campo vacío.
VACIO_OFAC = "-0-"

# ---------------------------------------------------------------------------
# 2. TABLAS DE TRADUCCIÓN
# ---------------------------------------------------------------------------
# Tipo de registro: en sdn.csv la tercera columna dice "individual", "vessel",
# "aircraft" o "-0-". El "-0-" significa que es una entidad (empresa, etc.).
TIPOS_REGISTRO = {
    "individual": "persona natural",
    "vessel": "barco",
    "aircraft": "aeronave",
    VACIO_OFAC: "persona juridica",
}

# Tipos de documento que buscamos dentro de remarks.
# A la izquierda: cómo lo escribe OFAC (en inglés, como expresión regular).
# A la derecha: el nombre en español que irá en la columna tipo_documento.
# Revisé todos los remarks del archivo para armar esta lista. Se dejaron por
# fuera cosas que NO son documentos (teléfonos, fechas, "Executive Order", etc.).
TIPOS_DOCUMENTO = {
    # --- Colombia y Latinoamérica ---
    r"C[eé]dula": "cédula",
    r"NIT": "NIT",
    r"RUC": "RUC",
    r"RIF": "RIF",
    r"R\.?F\.?C\.?": "RFC",
    r"C\.U\.R\.P\.": "CURP",
    r"C\.U\.I\.T\.": "CUIT",
    r"C\.U\.I\.P\.": "CUIP",
    r"C\.U\.I\.": "CUI",
    r"D\.N\.I\.": "DNI",
    r"RTN": "RTN",
    r"Matricula Mercantil": "matrícula mercantil",
    r"Folio Mercantil": "folio mercantil",
    r"Tarjeta de Identidad": "tarjeta de identidad",
    r"Numero de Identidad": "número de identidad",
    r"Credencial electoral": "credencial electoral",
    r"I\.F\.E\.": "credencial electoral",
    r"Electoral Registry": "credencial electoral",
    r"Cartilla de Servicio Militar Nacional": "libreta militar",
    # --- Documentos personales ---
    r"Diplomatic Passport": "pasaporte diplomático",
    r"British National Overseas Passport": "pasaporte",
    r"Stateless Person Passport": "pasaporte",
    r"Passport": "pasaporte",
    r"Stateless Person ID Card": "documento de identidad",
    r"Refugee ID Card": "documento de identidad",
    r"Kenyan ID": "documento nacional de identidad",
    r"Tazkira National ID Card": "documento nacional de identidad",
    r"Moroccan Personal ID": "documento nacional de identidad",
    r"CNP \(Personal Numerical Code\)": "documento nacional de identidad",
    r"N\.I\.E\.": "documento de identidad de extranjero",
    r"Seafarer's Identification Document": "documento de marino",
    r"National ID(?: Card)?": "documento nacional de identidad",
    r"National Foreign ID Number": "documento de identidad de extranjero",
    r"Personal ID Card": "documento de identidad",
    r"Citizen's Card Number": "documento de identidad",
    r"Identification Number": "número de identificación",
    r"Driver's License": "licencia de conducción",
    r"Birth Certificate Number": "registro civil de nacimiento",
    r"Residency Number": "permiso de residencia",
    r"Travel Document Number": "documento de viaje",
    r"SSN": "número de seguro social (EE. UU.)",
    r"Turkish Identification Number": "documento nacional de identidad",
    # --- Documentos tributarios y de empresas ---
    r"Tax ID": "identificación tributaria",
    r"US FEIN": "identificación tributaria",
    r"N\.I\.F\.": "identificación tributaria",
    r"C\.I\.F\.": "identificación tributaria",
    r"(?:Italian )?Fiscal Code": "identificación tributaria",
    r"V\.A\.T\. Number": "número de IVA (VAT)",
    r"Unified Social Credit Code \(USCC\)": "código USCC (China)",
    r"United Social Credit Code Certificate \(USCCC\)": "código USCC (China)",
    r"Legal Entity Number": "código LEI",
    r"Business Registration Number": "registro mercantil",
    r"Business Registration Document": "registro mercantil",
    r"Commercial Registry Number": "registro mercantil",
    r"Chamber of Commerce Number": "registro mercantil",
    r"Registration Number": "número de registro",
    r"Registration ID": "número de registro",
    r"Company Number": "número de registro",
    r"UK Company Number": "número de registro",
    r"Business Number": "número de registro",
    r"Enterprise Number": "número de registro",
    r"Public Registration Number": "número de registro",
    r"Central Registration System Number": "número de registro",
    r"C\.R\.": "número de registro",
    r"Trade License": "licencia comercial",
    r"License": "licencia",
    r"Government Gazette Number": "número Government Gazette",
    r"Economic Register Number \(CBLS\)": "registro económico (CBLS)",
    r"Entity Code": "código de entidad",
}

# Unimos todos los tipos en una sola expresión regular.
# Los ordenamos de más largo a más corto para que, por ejemplo,
# "Diplomatic Passport" se reconozca antes que "Passport".
_etiquetas = sorted(TIPOS_DOCUMENTO, key=len, reverse=True)
PATRON_DOCUMENTO = re.compile(
    r"^(?:alt\.\s*)?"                           # a veces empieza con "alt." (alterno)
    r"(?P<etiqueta>" + "|".join(_etiquetas) + r")"  # el tipo de documento
    r"(?:\s*(?:No\.?|#|:))?\s+"                 # "No.", "#" o ":" (opcionales)
    r"(?P<numero>.+?)"                          # el número del documento
    r"(?:\s*\((?P<pais>[^()]+)\))?"             # el país entre paréntesis (opcional)
    r"(?:\s+(?:issued|expires)\b.*)?"           # fechas de expedición/vencimiento (se ignoran)
    r"\s*\.?\s*$"                               # punto final opcional
)


# ---------------------------------------------------------------------------
# 3. FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------
def limpiar(valor):
    """Quita espacios sobrantes y convierte "-0-" en texto vacío."""
    valor = valor.strip()
    if valor == VACIO_OFAC:
        return ""
    return valor


def leer_csv(ruta):
    """Lee un CSV de OFAC (sin encabezados) y devuelve una lista de filas.

    Se descartan las filas vacías o casi vacías: el archivo sdn.csv termina
    con un carácter especial de "fin de archivo" que no es un registro.
    """
    # latin-1 nunca falla al leer, y los archivos de OFAC usan ese tipo de texto.
    with open(ruta, encoding="latin-1", newline="") as archivo:
        return [fila for fila in csv.reader(archivo) if len(fila) > 1]


def buscar_etiqueta_espanol(etiqueta_ofac):
    """Recibe la etiqueta tal como la escribe OFAC y devuelve el nombre en español."""
    for patron, nombre_espanol in TIPOS_DOCUMENTO.items():
        if re.fullmatch(patron, etiqueta_ofac):
            return nombre_espanol
    return etiqueta_ofac  # no debería pasar, pero por si acaso


def normalizar_numero(numero, tipo_documento, pais):
    """Deja solo los dígitos del número de documento.

    Para los NIT colombianos quita el dígito de verificación (el que va
    después del guion). Ejemplo: "800123456-1" -> "800123456".
    """
    if tipo_documento == "NIT":
        if "-" in numero:
            # Nos quedamos con lo que está antes del último guion.
            numero = numero.rsplit("-", 1)[0]
        else:
            # Algunos NIT vienen sin guion y con 10 dígitos, es decir, con el
            # dígito de verificación pegado (ej. "9000420320"). Un NIT
            # colombiano tiene 9 dígitos + 1 de verificación, así que quitamos
            # el último.
            solo_digitos = re.sub(r"\D", "", numero)
            if pais == "Colombia" and len(solo_digitos) == 10:
                numero = solo_digitos[:-1]
    # \D significa "cualquier cosa que NO sea un dígito"; la reemplazamos por nada.
    return re.sub(r"\D", "", numero)


def extraer_documentos(remarks):
    """Busca todos los documentos dentro del texto de remarks.

    OFAC separa cada dato de remarks con ";". Revisamos cada pedazo y, si
    coincide con el patrón de documento, lo guardamos.
    Devuelve una lista de diccionarios (uno por documento).
    """
    documentos = []
    for pedazo in remarks.split(";"):
        coincidencia = PATRON_DOCUMENTO.match(pedazo.strip())
        if coincidencia is None:
            continue  # este pedazo no es un documento (fecha, alias, etc.)

        tipo = buscar_etiqueta_espanol(coincidencia.group("etiqueta"))
        numero = coincidencia.group("numero").strip()
        pais = (coincidencia.group("pais") or "").strip()

        # Si el "número" no tiene ningún dígito, no es un documento real.
        if not re.search(r"\d", numero):
            continue

        documentos.append({
            "tipo_documento": tipo,
            "numero_documento": numero,
            "numero_normalizado": normalizar_numero(numero, tipo, pais),
            "pais_documento": pais,
        })
    return documentos


def limpiar_programa(programa):
    """OFAC escribe varios programas así: 'SDGT] [IRGC'. Lo dejamos 'SDGT | IRGC'."""
    programa = limpiar(programa)
    partes = [p.strip() for p in re.split(r"\]\s*\[", programa) if p.strip()]
    return " | ".join(partes)


# ---------------------------------------------------------------------------
# 4. PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    # --- 4.1 Leer la continuación de remarks (sdn_comments.csv) ---
    # Creamos un diccionario: id -> texto de continuación.
    continuaciones = {}
    for fila in leer_csv(ARCHIVO_COMENTARIOS):
        id_ofac = fila[0].strip()
        continuaciones[id_ofac] = continuaciones.get(id_ofac, "") + limpiar(fila[1])

    # --- 4.2 Leer las direcciones (add.csv) y quedarnos con los países ---
    # Columnas de add.csv: id, id_direccion, dirección, ciudad, PAÍS, observaciones
    paises_por_id = {}
    for fila in leer_csv(ARCHIVO_DIRECCIONES):
        id_ofac = fila[0].strip()
        pais = limpiar(fila[4])
        lista = paises_por_id.setdefault(id_ofac, [])
        if pais and pais not in lista:   # evitamos repetir el mismo país
            lista.append(pais)

    # --- 4.3 Recorrer la lista principal (sdn.csv) ---
    # Columnas de sdn.csv: 0 id, 1 nombre, 2 tipo, 3 programa, ..., 11 remarks
    filas_salida = []
    total_registros = 0
    registros_con_documento = 0

    for fila in leer_csv(ARCHIVO_SDN):
        total_registros += 1
        id_ofac = fila[0].strip()

        # Unimos el remarks con su continuación. OFAC corta el texto a la
        # mitad (incluso a mitad de palabra), así que se pegan sin espacio.
        remarks = limpiar(fila[11]) + continuaciones.get(id_ofac, "")

        datos_registro = {
            "id_ofac": id_ofac,
            "nombre": limpiar(fila[1]),
            "tipo_registro": TIPOS_REGISTRO.get(fila[2].strip(), fila[2].strip()),
            "pais_direccion": " | ".join(paises_por_id.get(id_ofac, [])),
            "programa_sancion": limpiar_programa(fila[3]),
        }

        documentos = extraer_documentos(remarks)
        if documentos:
            registros_con_documento += 1
        else:
            # Sin documentos: igual incluimos el registro con columnas vacías.
            documentos = [{"tipo_documento": "", "numero_documento": "",
                           "numero_normalizado": "", "pais_documento": ""}]

        # Una fila de salida por cada documento.
        for documento in documentos:
            filas_salida.append({**datos_registro, **documento})

    # --- 4.4 Guardar el resultado ---
    columnas = ["id_ofac", "nombre", "tipo_registro", "tipo_documento",
                "numero_documento", "numero_normalizado", "pais_documento",
                "pais_direccion", "programa_sancion"]

    # - delimiter=";"  -> separador punto y coma (Excel en configuración Colombia)
    # - utf-8-sig      -> Excel reconoce bien las tildes
    # - QUOTE_ALL      -> todo va entre comillas; los números se guardan como texto
    #                     (el csv no pierde ceros; ver nota sobre Excel en el resumen)
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";",
                                  quoting=csv.QUOTE_ALL)
        escritor.writeheader()
        escritor.writerows(filas_salida)

    # --- 4.5 Mostrar el resumen ---
    documentos_reales = [f for f in filas_salida if f["tipo_documento"]]
    colombianos = Counter(f["tipo_documento"] for f in documentos_reales
                          if f["pais_documento"] == "Colombia")

    print(f"Archivo generado: {ARCHIVO_SALIDA.name}")
    print(f"Filas en el archivo:               {len(filas_salida):>7,}")
    print(f"Total de registros SDN:            {total_registros:>7,}")
    print(f"Registros con al menos 1 documento:{registros_con_documento:>7,}")
    print(f"Registros sin documentos:          {total_registros - registros_con_documento:>7,}")
    print(f"Total de documentos extraídos:     {len(documentos_reales):>7,}")
    print("\nDocumentos colombianos por tipo:")
    for tipo, cantidad in colombianos.most_common():
        print(f"  {tipo:<35}{cantidad:>5}")
    print(f"  {'TOTAL':<35}{sum(colombianos.values()):>5}")


# Esto hace que main() se ejecute solo cuando corremos el archivo directamente.
if __name__ == "__main__":
    main()
