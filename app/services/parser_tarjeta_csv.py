"""
Parser de extractos de tarjeta para SGPEG.

Acepta CSV con separador ; o , y cabeceras flexibles.
Columnas reconocidas (case-insensitive):
  fecha:    fecha, fecha_operacion, date, f.operacion
  concepto: concepto, descripcion, descripcion_operacion, comercio, detalle
  importe:  importe, importe_euros, amount, cargo, abono
"""

import csv
import hashlib
import io
import re
from datetime import datetime


def _normalizar_fecha(texto: str) -> str | None:
    texto = texto.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalizar_importe(texto: str) -> float | None:
    texto = texto.strip().replace(" ", "").replace("€", "")
    # Detectar si usa punto como separador de miles y coma como decimal
    if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", texto):
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _ref_tarjeta(id_tarjeta: int, fecha: str, concepto: str, importe: float) -> str:
    raw = f"{id_tarjeta}|{fecha}|{concepto.strip().upper()}|{round(importe, 2)}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
    return f"CSV-TARJETA-{id_tarjeta}-{h}"


_ALIAS_FECHA     = {"fecha", "fecha_operacion", "date", "f.operacion", "f operacion", "fecha oper"}
_ALIAS_CONCEPTO  = {"concepto", "descripcion", "descripcion_operacion", "comercio", "detalle", "descripcion operacion"}
_ALIAS_IMPORTE   = {"importe", "importe_euros", "importe euros", "amount", "cargo", "importe (eur)", "importe(eur)"}


def _encontrar_col(cabeceras: list[str], alias_set: set) -> int | None:
    for i, h in enumerate(cabeceras):
        if h.lower().strip() in alias_set:
            return i
    return None


def parsear_csv_tarjeta(contenido: str, id_tarjeta: int, id_usuario: str) -> list[dict]:
    """Devuelve lista de dicts listos para crear_movimiento en mock_movimientos_tarjeta."""
    # Detectar separador
    separador = ";" if contenido.count(";") > contenido.count(",") else ","

    reader = csv.reader(io.StringIO(contenido), delimiter=separador)
    filas = list(reader)
    if not filas:
        return []

    # Buscar fila de cabecera (primera fila con palabras reconocidas)
    idx_cabecera = 0
    for i, fila in enumerate(filas):
        cabeceras_lower = [c.lower().strip() for c in fila]
        if any(c in _ALIAS_FECHA | _ALIAS_CONCEPTO | _ALIAS_IMPORTE for c in cabeceras_lower):
            idx_cabecera = i
            break

    cabeceras = [c.lower().strip() for c in filas[idx_cabecera]]
    col_fecha    = _encontrar_col(cabeceras, _ALIAS_FECHA)
    col_concepto = _encontrar_col(cabeceras, _ALIAS_CONCEPTO)
    col_importe  = _encontrar_col(cabeceras, _ALIAS_IMPORTE)

    if col_fecha is None or col_importe is None:
        raise ValueError("No se encontraron columnas de fecha e importe. Comprueba el formato del CSV.")

    movimientos = []
    for fila in filas[idx_cabecera + 1:]:
        if not fila or all(c.strip() == "" for c in fila):
            continue
        try:
            fecha_raw = fila[col_fecha].strip() if col_fecha is not None and col_fecha < len(fila) else ""
            concepto  = fila[col_concepto].strip() if col_concepto is not None and col_concepto < len(fila) else "Sin descripción"
            imp_raw   = fila[col_importe].strip() if col_importe < len(fila) else ""
        except IndexError:
            continue

        fecha = _normalizar_fecha(fecha_raw)
        if not fecha:
            continue

        importe = _normalizar_importe(imp_raw)
        if importe is None:
            continue

        referencia = _ref_tarjeta(id_tarjeta, fecha, concepto, importe)

        movimientos.append({
            "id_tarjeta":        id_tarjeta,
            "fecha_operacion":   fecha,
            "fecha_valor":       fecha,
            "concepto":          concepto,
            "importe":           importe,
            "referencia":        referencia,
            "estado":            "PENDIENTE",
            "id_usuario_importa": id_usuario,
        })

    return movimientos
