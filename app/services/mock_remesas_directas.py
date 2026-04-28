"""
Almacén en memoria de Remesas Directas.

Una RemesaDirecta es un gasto ya ejecutado por el banco (comisión,
domiciliación, suministro, etc.) que el gestor económico registra
directamente desde el movimiento bancario. No genera SEPA XML.
Lleva una o varias líneas de contabilidad analítica (departamento +
cuenta analítica + importe) que pueden sumar el total del movimiento
repartido entre distintos centros de coste.
"""

from datetime import datetime

_remesas_directas: list[dict] = []
_seq = 1


# ── TIPOS DE GASTO ────────────────────────────────────────────────────────────

TIPOS_GASTO = [
    "COMISION_BANCARIA",
    "DOMICILIACION",
    "SUMINISTRO",
    "SERVICIO_EXTERNO",
    "GASTO_PERSONAL",
    "IMPUESTO",
    "OTROS",
]


# ── CRUD ──────────────────────────────────────────────────────────────────────

def crear_remesa_directa(datos: dict) -> dict:
    """
    Crea una remesa directa con sus líneas analíticas.

    `datos` debe contener:
        id_movimiento   int
        id_banco        int
        descripcion     str
        tipo_gasto      str
        importe_total   float
        lineas          list[dict]  — cada dict: departamento, cuenta_analitica,
                                      descripcion_linea, importe
        id_usuario      str
    """
    global _seq
    rd = {
        "id_remesa_directa": _seq,
        "id_movimiento":     datos["id_movimiento"],
        "ids_movimientos":   datos.get("ids_movimientos", [datos["id_movimiento"]]),
        "id_banco":          datos["id_banco"],
        "descripcion":       datos["descripcion"],
        "tipo_gasto":        datos["tipo_gasto"],
        "cuenta_gasto":      datos.get("cuenta_gasto", ""),
        "importe_total":     round(datos["importe_total"], 2),
        "estado":            "COTEJADA",
        "lineas":            [],
        "id_usuario_crea":   datos["id_usuario"],
        "fecha_creacion":    datetime.now().strftime("%Y-%m-%d"),
    }
    seq_linea = 1
    for linea in datos.get("lineas", []):
        importe = linea.get("importe", 0.0)
        if importe == 0:
            continue
        rd["lineas"].append({
            "id_linea":          seq_linea,
            "tipo_gasto":        linea.get("tipo_gasto", "").strip(),
            "cuenta_gasto":      linea.get("cuenta_gasto", "").strip(),
            "servicio_proyecto": linea.get("servicio_proyecto", "").strip(),
            "descripcion_linea": linea.get("descripcion_linea", "").strip(),
            "porcentaje":        round(linea.get("porcentaje", 0.0), 2),
            "importe":           round(importe, 2),
        })
        seq_linea += 1

    _remesas_directas.append(rd)
    _seq += 1
    return rd


def listar_remesas_directas(id_movimiento: int | None = None) -> list[dict]:
    if id_movimiento is not None:
        return [r for r in _remesas_directas if r["id_movimiento"] == id_movimiento]
    return list(_remesas_directas)


def obtener_remesa_directa(id_rd: int) -> dict | None:
    return next((r for r in _remesas_directas if r["id_remesa_directa"] == id_rd), None)


def existe_remesa_directa_para(id_movimiento: int) -> bool:
    return any(r["id_movimiento"] == id_movimiento for r in _remesas_directas)
