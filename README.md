# Consulta de contratistas en listas restrictivas

Página web donde cualquier persona sube el Excel de contratistas y ve, en segundos, si alguno aparece en:

- la **Lista SDN de OFAC** ("Lista Clinton"), incluidos los alias, y
- la **Lista Consolidada del Consejo de Seguridad de la ONU**.

El archivo de contratistas **se revisa dentro del navegador** de quien lo sube: no se envía a ningún servidor.
Las listas se actualizan solas cada lunes.

## Qué hay en el repositorio

| Archivo o carpeta | Para qué sirve |
|---|---|
| `index.html` | La página que ven los usuarios. |
| `motor.js` | La lógica del cruce (la misma de `cruce_listas.py`, en JavaScript). |
| `xlsx.full.min.js` | Librería SheetJS para leer y escribir archivos de Excel en el navegador. |
| `datos/listas.json` | Las listas de OFAC y ONU ya procesadas. Se regenera automáticamente. |
| `procesamiento/` | Los scripts de Python que descargan y procesan las listas. |
| `.github/workflows/` | La tarea automática que actualiza las listas y publica la página. |

## Cómo se busca

| Alerta | Cuándo aparece |
|---|---|
| Alta | El documento (cédula o NIT) es igual a uno de la lista. Si el NIT trae dígito de verificación, también se busca sin él. |
| Media | El nombre es igual, sin importar el orden de las palabras, las tildes ni el tipo de sociedad (S.A.S., LTDA…). |
| Baja | El nombre es muy parecido (similitud de 90 o más sobre 100). |

La página reconoce sola las columnas de documento y nombre buscando encabezados como "NIT", "cédula", "documento", "identificación", "nombre" o "razón social", aunque estén después de filas de título (como en los reportes de SAP). Si no las reconoce, le pide al usuario elegirlas.

## Montarlo en GitHub (una sola vez)

1. **Crear el repositorio.** En github.com, botón **New repository**. Póngale un nombre, por ejemplo `consulta-listas-restrictivas`.
   - Si lo crea **privado**, GitHub Pages solo funciona con un plan pago (Pro, Team o Enterprise).
   - Si lo crea **público**, cualquiera puede ver el código y las listas (que de todas formas son públicas). Los archivos de contratistas nunca se suben, así que no quedan expuestos.
2. **Subir los archivos.** En el repositorio vacío, **Add file > Upload files**, y arrastre todo el contenido de esta carpeta, incluida la carpeta `.github`. Luego **Commit changes**.
   - Si Windows no deja arrastrar la carpeta `.github`, créela a mano: **Add file > Create new file**, escriba como nombre `.github/workflows/actualizar_y_publicar.yml` y pegue el contenido de ese archivo.
3. **Activar la página.** En **Settings > Pages**, en "Source" elija **GitHub Actions**.
4. **Primera publicación.** En la pestaña **Actions**, elija **Actualizar listas y publicar** y pulse **Run workflow**. En unos minutos aparece en verde, y en **Settings > Pages** se ve la dirección de la página (algo como `https://usuario.github.io/consulta-listas-restrictivas/`).

## Mantenimiento

- **Actualización automática:** cada lunes a las 6:00 a. m. Para cambiar la frecuencia, edite la línea `cron` del archivo de la tarea. Ejemplo: `"0 11 * * *"` es todos los días.
- **Actualizar a mano:** pestaña **Actions > Actualizar listas y publicar > Run workflow**.
- **Si la tarea falla** (por ejemplo, porque la página de OFAC o de la ONU no respondió), la página sigue funcionando con las listas anteriores. GitHub envía un correo avisando; basta con volver a correrla más tarde.
- **Si GitHub pausa la tarea programada** por inactividad del repositorio, aparece un aviso en la pestaña Actions con un botón para reactivarla.
- **Cambiar qué tan estricta es la búsqueda por nombre parecido:** en `motor.js`, la línea `var UMBRAL_SIMILITUD = 90;`.
- **Revisar la fecha de las listas:** aparece siempre en la parte de arriba de la página y en la hoja "Resumen" del Excel descargado.

## Probar la página en el computador

La página no funciona abriendo `index.html` con doble clic, porque el navegador bloquea la carga de `datos/listas.json` desde archivos locales. Para probarla:

```
python -m http.server 8000
```

y abra `http://localhost:8000` en el navegador.

## Cuidados

- **Nunca suba al repositorio bases de contratistas ni resultados de cruces.** El archivo `.gitignore` bloquea los Excel, pero solo cuando se usa Git; al subir archivos por la página de GitHub hay que tener el cuidado a mano.
- Una coincidencia no significa que el contratista esté sancionado: puede ser un homónimo. Cada alerta se verifica con documento, país y fecha de nacimiento.
- La búsqueda por nombre parecido revisa los nombres que comparten al menos una palabra, o el inicio o el final de una palabra. En pruebas con errores de digitación encontró el 99,5 % de los casos que encuentra la versión de Python; los que se escapan son nombres muy cortos de una o dos palabras con el error en la mitad.
