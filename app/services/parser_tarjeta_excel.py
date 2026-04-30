"""
Parsers de Excel para movimientos de tarjeta usando pandas.

· Santander  → .xlsx  — hoja "Liquidación mensual", cabeceras en fila 17 (pandas header=16)
· Unicaja    → .xls   — hoja "Unicaja01",           cabeceras en fila 11 (pandas header=10)
"""
import io
import re
import zipfile
from datetime import datetime


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _normalizar_fecha(valor) -> str:
    """Convierte DD/MM/YYYY (str), datetime o Timestamp a YYYY-MM-DD."""
    if valor is None:
        return ""
    if hasattr(valor, "strftime"):       # datetime / pandas Timestamp
        return valor.strftime("%Y-%m-%d")
    s = str(valor).strip().split(" ")[0]  # quitar hora si la hay
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _normalizar_importe(valor) -> float:
    """Acepta float, int o str con coma decimal tipo '-30,95'."""
    if valor is None:
        return 0.0
    try:
        import math
        if math.isnan(float(valor)):
            return 0.0
    except (TypeError, ValueError):
        pass
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace("\xa0", "").replace(" ", "")
    # "1.234,56" → punto como millar, coma como decimal
    if s.count(",") == 1 and "." in s and s.rindex(".") < s.index(","):
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _referencia(id_tarjeta: int, fecha: str, concepto: str, importe: float) -> str:
    return f"T{id_tarjeta}|{fecha}|{concepto[:40]}|{importe:.2f}"


def _buscar_columna(df_cols: list, nombres: list[str]) -> str | None:
    """Devuelve el nombre real de la columna que coincide con alguno de los alias."""
    for n in nombres:
        n_low = n.lower().strip()
        for col in df_cols:
            if str(col).lower().strip() == n_low:
                return col
    return None


def _reparar_xlsx(contenido_bytes: bytes) -> bytes:
    """
    Algunos xlsx generados por bancos incluyen valores de atributo 'state' no estándar
    en workbook.xml (p.ej. 'active') que openpyxl rechaza. Los eliminamos antes de parsear.
    """
    buf = io.BytesIO(contenido_bytes)
    try:
        with zipfile.ZipFile(buf) as z:
            archivos = {n: z.read(n) for n in z.namelist()}
    except zipfile.BadZipFile:
        return contenido_bytes  # no es un xlsx válido; dejar que falle más tarde

    if "xl/workbook.xml" in archivos:
        wb_xml = archivos["xl/workbook.xml"].decode("utf-8", errors="replace")
        # Eliminar atributo state= con cualquier valor (openpyxl pone 'visible' por defecto)
        wb_xml_fixed = re.sub(r'\s+state="[^"]*"', "", wb_xml)
        archivos["xl/workbook.xml"] = wb_xml_fixed.encode("utf-8")

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z2:
        for nombre, datos in archivos.items():
            z2.writestr(nombre, datos)
    return out.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# SANTANDER  (.xlsx)
# ──────────────────────────────────────────────────────────────────────────────

def parsear_excel_santander(contenido_bytes: bytes, id_tarjeta: int, id_usuario: str) -> list[dict]:
    """
    Hoja "Liquidación mensual".
    Cabeceras en la fila 17 (base-1) → header=16 en pandas (base-0).
    Columnas: 'Fecha operación', 'Concepto', 'Beneficiario', 'Importe'.
    Importe: float numérico (negativo = cargo).
    """
    import pandas as pd

    # Reparar posibles valores de 'state' inválidos en workbook.xml
    contenido_reparado = _reparar_xlsx(contenido_bytes)

    try:
        df = pd.read_excel(
            io.BytesIO(contenido_reparado),
            sheet_name="Liquidación mensual",
            header=16,          # fila 17 (base-1)
            engine="openpyxl",
        )
    except Exception:
        # Fallback: primera hoja
        try:
            df = pd.read_excel(
                io.BytesIO(contenido_reparado),
                sheet_name=0,
                header=16,
                engine="openpyxl",
            )
        except Exception as e:
            raise ValueError(f"No se pudo abrir el fichero Excel de Santander: {e}") from e

    cols = list(df.columns)

    c_fecha    = _buscar_columna(cols, ["Fecha operación", "Fecha Operación", "Fecha operacion", "Fecha"])
    c_concepto = _buscar_columna(cols, ["Concepto", "Descripción", "Descripcion"])
    c_benefic  = _buscar_columna(cols, ["Beneficiario", "Nombre"])
    c_importe  = _buscar_columna(cols, ["Importe", "Cargo", "Amount"])

    if c_fecha is None or c_importe is None:
        raise ValueError(
            f"No se encontraron las columnas esperadas en el Excel de Santander. "
            f"Columnas detectadas: {cols}"
        )

    movimientos = []
    for _, row in df.iterrows():
        fecha   = _normalizar_fecha(row.get(c_fecha))
        importe = _normalizar_importe(row.get(c_importe))

        if not fecha or importe == 0.0:
            continue

        concepto_base = str(row.get(c_concepto, "") or "").strip()
        beneficiario  = str(row.get(c_benefic,  "") or "").strip() if c_benefic else ""
        desc = " – ".join(filter(None, [beneficiario, concepto_base])) or "Sin concepto"

        ref = _referencia(id_tarjeta, fecha, desc, importe)
        movimientos.append({
            "id_tarjeta":      id_tarjeta,
            "fecha_operacion": fecha,
            "fecha_valor":     fecha,
            "concepto":        desc,
            "importe":         round(importe, 2),
            "referencia":      ref,
            "estado":          "PENDIENTE",
            "id_usuario":      id_usuario,
        })

    return movimientos


# ──────────────────────────────────────────────────────────────────────────────
# UNICAJA  (.xls)
# ──────────────────────────────────────────────────────────────────────────────

def parsear_excel_unicaja(contenido_bytes: bytes, id_tarjeta: int, id_usuario: str) -> list[dict]:
    """
    Hoja "Unicaja01".
    Cabeceras en la fila 11 (base-1) → header=10 en pandas (base-0).
    Columnas: 'Fecha operación', 'Nombre comercio', 'Concepto', 'Importe'.
    Importe: string con coma decimal tipo '-30,95'.
    """
    import pandas as pd

    try:
        df = pd.read_excel(
            io.BytesIO(contenido_bytes),
            sheet_name="Unicaja01",
            header=10,          # fila 11 (base-1)
            engine="xlrd",
        )
    except Exception:
        try:
            df = pd.read_excel(
                io.BytesIO(contenido_bytes),
                sheet_name=0,
                header=10,
                engine="xlrd",
            )
        except Exception as e:
            raise ValueError(f"No se pudo abrir el fichero Excel de Unicaja: {e}") from e

    cols = list(df.columns)

    c_fecha    = _buscar_columna(cols, ["Fecha operación", "Fecha Operación", "Fecha operacion", "Fecha"])
    c_comercio = _buscar_columna(cols, ["Nombre comercio", "Nombre Comercio", "Comercio", "Nombre"])
    c_concepto = _buscar_columna(cols, ["Concepto", "Descripción", "Descripcion"])
    c_importe  = _buscar_columna(cols, ["Importe", "Cargo", "Amount"])

    if c_fecha is None or c_importe is None:
        raise ValueError(
            f"No se encontraron las columnas esperadas en el Excel de Unicaja. "
            f"Columnas detectadas: {cols}"
        )

    movimientos = []
    for _, row in df.iterrows():
        fecha   = _normalizar_fecha(row.get(c_fecha))
        importe = _normalizar_importe(row.get(c_importe))

        if not fecha or importe == 0.0:
            continue

        comercio = str(row.get(c_comercio, "") or "").strip() if c_comercio else ""
        concepto = str(row.get(c_concepto, "") or "").strip() if c_concepto else ""
        desc = " – ".join(filter(None, [comercio, concepto])) or "Sin concepto"

        ref = _referencia(id_tarjeta, fecha, desc, importe)
        movimientos.append({
            "id_tarjeta":      id_tarjeta,
            "fecha_operacion": fecha,
            "fecha_valor":     fecha,
            "concepto":        desc,
            "importe":         round(importe, 2),
            "referencia":      ref,
            "estado":          "PENDIENTE",
            "id_usuario":      id_usuario,
        })

    return movimientos
