/*
 * MOTOR DE BÚSQUEDA
 * Misma lógica de cruce_listas.py, escrita en JavaScript para que funcione
 * dentro del navegador. El archivo de contratistas nunca sale del computador.
 *
 *   1. Documento igual            -> alerta ALTA
 *   2. Nombre igual (cualquier orden de palabras) -> alerta MEDIA
 *   3. Nombre parecido (>= UMBRAL_SIMILITUD)       -> alerta BAJA
 */

var UMBRAL_SIMILITUD = 90;

var PALABRAS_SOCIEDAD = new Set(["SAS", "SA", "LTDA", "LIMITADA", "LTD", "INC", "LLC", "CIA", "ESP", "EU"]);

/* ---------- Limpieza (igual que en Python) ---------- */

function limpiarNombre(nombre) {
  if (nombre === null || nombre === undefined) return "";
  var texto = String(nombre).replace(/\./g, "");                 // S.A.S. -> SAS
  texto = texto.normalize("NFKD").replace(/[\u0300-\u036f]/g, ""); // quita tildes
  texto = texto.replace(/[^A-Za-z0-9 ]/g, " ").toUpperCase();
  return texto.split(/\s+/).filter(function (p) { return p && !PALABRAS_SOCIEDAD.has(p); }).join(" ");
}

function ordenarPalabras(nombreLimpio) {
  return nombreLimpio.split(" ").filter(Boolean).sort().join(" ");
}

function limpiarDocumento(doc) {
  if (doc === null || doc === undefined) return "";
  var texto = String(doc).trim();
  if (/\.0$/.test(texto)) texto = texto.slice(0, -2);            // Excel a veces agrega .0
  return texto.replace(/[^A-Za-z0-9]/g, "").toUpperCase().replace(/^0+/, "");
}

/* Si parece un NIT con dígito de verificación, también se busca sin él. */
function variantesDocumento(doc) {
  var variantes = [doc];
  if (doc.length === 10 && /^\d+$/.test(doc) && (doc[0] === "8" || doc[0] === "9")) {
    variantes.push(doc.slice(0, 9));
  }
  return variantes;
}

/* Similitud de 0 a 100, igual a fuzz.ratio de rapidfuzz:
   200 * (letras en común en orden) / (largo1 + largo2) */
function similitud(a, b) {
  if (a === b) return 100;
  var n = a.length, m = b.length;
  if (!n || !m) return 0;
  var anterior = new Uint16Array(m + 1), actual = new Uint16Array(m + 1);
  for (var i = 1; i <= n; i++) {
    var ca = a.charCodeAt(i - 1);
    for (var j = 1; j <= m; j++) {
      if (ca === b.charCodeAt(j - 1)) actual[j] = anterior[j - 1] + 1;
      else actual[j] = actual[j - 1] > anterior[j] ? actual[j - 1] : anterior[j];
    }
    var t = anterior; anterior = actual; actual = t;
  }
  return 200 * anterior[m] / (n + m);
}

/* ---------- Preparar las listas (se hace una vez al abrir la página) ---------- */

function prepararListas(datos) {
  var nombres = datos.nombres.map(function (n) {
    var ordenado = ordenarPalabras(limpiarNombre(n[1]));
    return { reg: n[0], nombre: n[1], tipoNombre: n[2], ordenado: ordenado };
  }).filter(function (n) { return n.ordenado; });

  var porNombreExacto = new Map();   // nombre ordenado -> posiciones
  var porPalabra = new Map();        // palabra o inicio de palabra -> posiciones
  nombres.forEach(function (n, pos) {
    if (!porNombreExacto.has(n.ordenado)) porNombreExacto.set(n.ordenado, []);
    porNombreExacto.get(n.ordenado).push(pos);
    clavesPalabras(n.ordenado).forEach(function (clave) {
      if (!porPalabra.has(clave)) porPalabra.set(clave, []);
      porPalabra.get(clave).push(pos);
    });
  });

  var porDocumento = new Map();
  datos.documentos.forEach(function (d) {
    if (!porDocumento.has(d[1])) porDocumento.set(d[1], []);
    porDocumento.get(d[1]).push(d);
  });

  return { meta: datos.meta, registros: datos.registros, nombres: nombres,
           porNombreExacto: porNombreExacto, porPalabra: porPalabra, porDocumento: porDocumento };
}

/* Para no comparar cada contratista contra los 43.000 nombres, solo se comparan
   los nombres que comparten al menos una palabra completa, o sus 4 primeras
   o 4 últimas letras. */
function clavesPalabras(nombreOrdenado) {
  var claves = new Set();
  nombreOrdenado.split(" ").forEach(function (p) {
    if (p.length >= 2) claves.add("P:" + p);
    if (p.length >= 4) {
      claves.add("I:" + p.slice(0, 4));   // primeras 4 letras
      claves.add("F:" + p.slice(-4));     // últimas 4 letras
    }
  });
  return claves;
}

/* ---------- Búsqueda de un contratista ---------- */

function buscarContratista(listas, documento, nombre) {
  var alertas = [];
  var doc = limpiarDocumento(documento);
  var ordenado = ordenarPalabras(limpiarNombre(nombre));

  function datosRegistro(pos) {
    var r = listas.registros[pos];
    return { fuente: r[0], idLista: r[1], nombrePrincipal: r[2], tipoRegistro: r[3], programa: r[4] };
  }

  // 1. Documento
  if (doc) {
    variantesDocumento(doc).forEach(function (v) {
      (listas.porDocumento.get(v) || []).forEach(function (d) {
        var r = datosRegistro(d[0]);
        alertas.push(Object.assign(r, {
          nivel: 1, tipoCoincidencia: "Documento", similitud: 100,
          nombreEnLista: r.nombrePrincipal, tipoNombre: "",
          documentoEnLista: d[1], detalleDocumento: (d[2] + " " + d[3]).trim()
        }));
      });
    });
  }

  if (ordenado) {
    // 2. Nombre exacto
    (listas.porNombreExacto.get(ordenado) || []).forEach(function (pos) {
      var n = listas.nombres[pos], r = datosRegistro(n.reg);
      alertas.push(Object.assign(r, {
        nivel: 2, tipoCoincidencia: "Nombre exacto", similitud: 100,
        nombreEnLista: n.nombre, tipoNombre: n.tipoNombre, documentoEnLista: "", detalleDocumento: ""
      }));
    });

    // 3. Nombre parecido
    var candidatos = new Set();
    clavesPalabras(ordenado).forEach(function (clave) {
      (listas.porPalabra.get(clave) || []).forEach(function (pos) { candidatos.add(pos); });
    });
    var largo = ordenado.length;
    candidatos.forEach(function (pos) {
      var n = listas.nombres[pos];
      if (n.ordenado === ordenado) return;                       // ya es exacto
      var minimo = Math.min(largo, n.ordenado.length);
      if (200 * minimo / (largo + n.ordenado.length) < UMBRAL_SIMILITUD) return; // largos muy distintos
      var puntaje = similitud(ordenado, n.ordenado);
      if (puntaje >= UMBRAL_SIMILITUD) {
        var r = datosRegistro(n.reg);
        alertas.push(Object.assign(r, {
          nivel: 3, tipoCoincidencia: "Nombre similar", similitud: Math.round(puntaje * 10) / 10,
          nombreEnLista: n.nombre, tipoNombre: n.tipoNombre, documentoEnLista: "", detalleDocumento: ""
        }));
      }
    });
  }

  // Un mismo registro de la lista se reporta una sola vez, con la coincidencia más fuerte
  alertas.sort(function (a, b) { return a.nivel - b.nivel || b.similitud - a.similitud; });
  var vistos = new Set();
  return alertas.filter(function (a) {
    var clave = a.fuente + "|" + a.idLista;
    if (vistos.has(clave)) return false;
    vistos.add(clave);
    return true;
  });
}

/* ---------- Encontrar las columnas de documento y nombre ---------- */

function normalizarEncabezado(texto) {
  return String(texto || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function puntajeDocumento(encabezado) {
  var e = " " + normalizarEncabezado(encabezado) + " ";
  if (/ (nit|cedula|ced|cc|documento|identificacion|nro id|no id|num id|numero id) /.test(e)) return 3;
  if (/ (id|identidad) /.test(e)) return 1;
  return 0;
}

function puntajeNombre(encabezado) {
  var e = " " + normalizarEncabezado(encabezado) + " ";
  if (/ nombre| razon social/.test(e)) return 3;
  if (/ (beneficiario|tercero|contratista|proveedor|acreedor) /.test(e)) return 1;
  return 0;
}

/* Recibe las filas de una hoja (lista de listas) y busca, en las primeras 30,
   la fila de encabezados que tenga una columna de documento y una de nombre. */
function detectarColumnas(filas) {
  for (var i = 0; i < Math.min(30, filas.length); i++) {
    var fila = filas[i] || [];
    var mejorDoc = -1, puntosDoc = 0, mejorNom = -1, puntosNom = 0;
    fila.forEach(function (celda, j) {
      if (typeof celda !== "string" || !celda.trim()) return;
      var pd = puntajeDocumento(celda);
      if (pd > puntosDoc) { puntosDoc = pd; mejorDoc = j; }
    });
    fila.forEach(function (celda, j) {
      if (typeof celda !== "string" || !celda.trim() || j === mejorDoc) return;
      var pn = puntajeNombre(celda);
      if (pn > puntosNom) { puntosNom = pn; mejorNom = j; }
    });
    if (mejorDoc >= 0 && mejorNom >= 0) {
      return { filaEncabezado: i, colDocumento: mejorDoc, colNombre: mejorNom };
    }
  }
  return null;
}

/* Primera fila con al menos dos celdas de texto: se usa como encabezado
   cuando no se reconocen las columnas automáticamente. */
function filaEncabezadoProbable(filas) {
  for (var i = 0; i < Math.min(30, filas.length); i++) {
    var textos = (filas[i] || []).filter(function (c) { return typeof c === "string" && c.trim(); });
    if (textos.length >= 2) return i;
  }
  return 0;
}

/* Convierte el valor de una celda en texto sin perder dígitos. */
function textoCelda(valor) {
  if (valor === null || valor === undefined) return "";
  if (typeof valor === "number") {
    return Number.isInteger(valor) ? valor.toFixed(0) : String(valor);
  }
  return String(valor).trim();
}

if (typeof module !== "undefined") {
  module.exports = { prepararListas: prepararListas, buscarContratista: buscarContratista,
    detectarColumnas: detectarColumnas, filaEncabezadoProbable: filaEncabezadoProbable,
    textoCelda: textoCelda, limpiarNombre: limpiarNombre, limpiarDocumento: limpiarDocumento,
    similitud: similitud };
}
