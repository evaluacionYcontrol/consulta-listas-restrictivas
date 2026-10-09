# Consulta de contratistas en listas restrictivas

**Secretaría de Evaluación y Control · Proyecto LA/FT/FPADM**
(Lavado de Activos, Financiación del Terrorismo y Financiación de la Proliferación de Armas de Destrucción Masiva)

Página web para verificar si un contratista aparece en listas restrictivas. Tiene dos formas de uso:

- **Revisión de un archivo:** se sube el Excel de contratistas (.xlsx, .xls o .csv) y la página revisa todas las filas.
- **Consulta individual:** se escribe la cédula o NIT, el nombre, o ambos, de una sola persona o empresa.

El resultado se ve en pantalla y se puede descargar en Excel como soporte de la verificación.

## Listas que se consultan

| Lista | Qué contiene | Fuente oficial |
|---|---|---|
| OFAC | Lista SDN de la Oficina de Control de Activos Extranjeros de EE. UU., con alias. Incluye las designaciones de terroristas de EE. UU. | sanctionslistservice.ofac.treas.gov |
| ONU | Lista Consolidada del Consejo de Seguridad de las Naciones Unidas. | scsanctions.un.org |
| Unión Europea | Personas y organizaciones catalogadas como terroristas por la UE (Posición Común 2001/931/PESC y régimen ISIL/Al-Qaida). | data.europa.eu, lista consolidada de sanciones financieras |
| BID | Firmas y personas inhabilitadas por prácticas prohibidas (fraude, corrupción, colusión). Incluye inhabilitaciones cruzadas de otros bancos multilaterales. Solo se incluyen las vigentes. | data.iadb.org |
| Banco Mundial | Firmas y personas inhabilitadas para contratos financiados por el Banco Mundial, con nombres alternos y números de registro mercantil. Solo se incluyen las vigentes. | worldbank.org/en/projects-operations/procurement/debarred-firms (exportación a Excel) |

Las listas se actualizan automáticamente cada lunes, excepto la del Banco Mundial, que se actualiza a mano (ver "Actualización de la lista del Banco Mundial"). La fecha de actualización aparece en la parte de arriba de la página y en el Excel descargado.

## Protección de los datos

Los archivos y consultas de contratistas **se procesan dentro del navegador** de quien usa la página (procesamiento del lado del cliente). No se envían a GitHub ni a ningún otro servidor. La única descarga que hace la página es la del archivo de listas (`datos/listas.json`), que contiene información pública.

Cómo se verificó:

1. **Inspección del tráfico de red** con las herramientas de desarrollo del navegador (tecla F12, pestaña Red o Network): durante la carga y revisión del archivo no aparece ninguna transmisión de datos.
2. **Prueba de funcionamiento sin conexión:** con el internet desconectado (o con la opción "Offline" de la pestaña Red), la revisión funciona igual.
3. **Revisión del código fuente:** la única instrucción de comunicación (`fetch`) en `index.html` y `motor.js` es la que descarga `datos/listas.json`.

## Cómo se busca

| Alerta | Tipo de coincidencia | Cuándo aparece |
|---|---|---|
| Alta | Documento | La cédula o NIT es igual a uno de la lista. Si el NIT trae dígito de verificación, también se busca sin él. Se ignoran puntos, guiones y ceros a la izquierda. |
| Media | Nombre exacto | El nombre es igual, sin importar el orden de las palabras, las tildes ni el tipo de sociedad (S.A.S., LTDA…). |
| Baja | Nombre similar | El nombre es muy parecido (similitud de 90 o más sobre 100), por ejemplo por errores de digitación. |
| Baja | Nombre parcial | Todas las palabras de un nombre están dentro del otro, con mínimo dos palabras. Ejemplo: "Verónica Alcocer" dentro de "Verónica del Socorro Alcocer García". Se ignoran conectores como "de" o "del". |

En las coincidencias por nombre, la columna **Motivo** muestra el documento que la lista tiene registrado para esa persona o empresa, para compararlo con el documento del contratista.

La página reconoce sola las columnas de documento y nombre buscando encabezados como "NIT", "cédula", "documento", "identificación", "nombre" o "razón social", aunque estén después de filas de título (como en los reportes de SAP). Si no las reconoce, le pide al usuario elegirlas.

**Una coincidencia no significa que el contratista esté sancionado:** puede ser un homónimo. Cada alerta debe verificarse con documento, país y fecha de nacimiento. La herramienta es un apoyo para detectar alertas, no un certificado oficial.

## Qué hay en el repositorio

| Archivo o carpeta | Para qué sirve |
|---|---|
| `index.html` | La página que ven los usuarios (diseño, textos, foto y logo). |
| `motor.js` | La lógica de búsqueda. |
| `xlsx.full.min.js` | Librería SheetJS para leer y escribir archivos de Excel en el navegador. |
| `datos/listas.json` | Las cinco listas ya procesadas. Se regenera automáticamente. |
| `procesamiento/descargar_listas.py` | Descarga las listas desde las fuentes oficiales. |
| `procesamiento/extraer_documentos_sdn.py` | Extrae los documentos de identidad de la lista OFAC. |
| `procesamiento/convertir_onu_a_csv.py` | Convierte la lista de la ONU (XML) a CSV. |
| `procesamiento/convertir_ue.py` | Extrae la lista de terroristas de la Unión Europea. |
| `procesamiento/convertir_bid.py` | Convierte la lista del BID y deja solo las inhabilitaciones vigentes. |
| `procesamiento/convertir_banco_mundial.py` | Convierte la lista del Banco Mundial y deja solo las inhabilitaciones vigentes. |
| `procesamiento/bm_fuente.xlsx` | Última lista del Banco Mundial descargada a mano. |
| `procesamiento/preparar_datos_web.py` | Une las cinco listas en `datos/listas.json`. |
| `.github/workflows/actualizar_y_publicar.yml` | La tarea automática que actualiza las listas y publica la página. |

## Actualización automática

Cada lunes a las 6:00 a. m. (hora Colombia), GitHub Actions ejecuta en orden: `descargar_listas.py`, `extraer_documentos_sdn.py`, `convertir_onu_a_csv.py`, `convertir_ue.py`, `convertir_bid.py`, `convertir_banco_mundial.py` y `preparar_datos_web.py`, y publica la página.

- **Actualizar a mano:** pestaña **Actions > Actualizar listas y publicar > Run workflow**.
- **Si falla una descarga,** no se actualiza ninguna lista y la página sigue funcionando con las anteriores. GitHub envía un correo avisando; basta con volver a correr la tarea más tarde.
- **Si alguna lista llega incompleta** (muchos menos registros de lo normal), tampoco se publica.
- **Si GitHub pausa la tarea programada** por inactividad del repositorio, aparece un aviso en la pestaña Actions con un botón para reactivarla.

## Actualización de la lista del Banco Mundial

El Banco Mundial no publica su lista con una dirección de descarga fija, así que se actualiza a mano (se recomienda una vez al mes):

1. Entrar a https://www.worldbank.org/en/projects-operations/procurement/debarred-firms
2. En la tabla "Debarred Firms and Individuals", usar la opción de exportar a Excel.
3. Renombrar el archivo descargado como `bm_fuente.xlsx`.
4. En el repositorio, entrar a la carpeta `procesamiento`, subir el archivo con **Add file > Upload files** y pulsar **Commit changes**.
5. En la pestaña **Actions**, lanzar **Actualizar listas y publicar > Run workflow**.

La fecha de la versión usada aparece en la sección "¿Qué listas se consultan?" de la página.

## Ajustes frecuentes

| Qué cambiar | Dónde |
|---|---|
| Qué tan parecido debe ser un nombre para alertar | `motor.js`, línea `var UMBRAL_SIMILITUD = 90;` |
| Mínimo de palabras para la búsqueda parcial | `motor.js`, línea `var MINIMO_PALABRAS_PARCIAL = 2;` |
| Incluir todas las sanciones de la UE, no solo terrorismo | `procesamiento/convertir_ue.py`, dejar `PROGRAMAS_UE = set()` |
| Frecuencia de actualización | Línea `cron` del archivo de la tarea. Ejemplo: `"0 11 * * *"` es todos los días. |
| Colores institucionales | Inicio de `index.html`, variables `--azul` y `--naranja`. |

## Administración

- El repositorio pertenece a la organización **evaluacionYcontrol**, no a una persona. Debe tener al menos dos administradores (rol Owner) con cuentas individuales y doble factor activo, más la cuenta genérica institucional como cuenta de respaldo, con sus credenciales bajo custodia.
- Cuando un administrador deja la entidad, otro lo retira de la organización y agrega a su reemplazo. La página y la tarea automática siguen funcionando sin cambios.
- Se recomienda activar la protección de la rama principal para que todo cambio requiera aprobación de otro administrador.

## Probar la página en el computador

La página no funciona abriendo `index.html` con doble clic, porque el navegador bloquea la carga de `datos/listas.json` desde archivos locales. Para probarla:

```
python -m http.server 8000
```

y abrir `http://localhost:8000` en el navegador.

## Cuidados

- **Nunca suba al repositorio bases de contratistas ni resultados de cruces.** El repositorio es público.
- **Comunique a los usuarios solo la dirección oficial de la página** y pídales guardarla en favoritos, para evitar copias falsas.
- **Antes del uso oficial,** reemplace `xlsx.full.min.js` por la versión más reciente publicada en el sitio oficial de SheetJS (cdn.sheetjs.com).
- La búsqueda por nombre parecido en la página compara los nombres que comparten al menos una palabra, o el inicio o el final de una palabra. En pruebas con errores de digitación encontró el 99,5 % de los casos que encuentra la versión en Python.
