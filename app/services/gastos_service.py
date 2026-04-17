from app.mock_data import GASTOS_DIRECTOS, TARJETAS
from app.services.pegs_service import _analiticas, _servicios
from app.services.proveedores_service import proveedores_db as _proveedores
from app.services.mock_usuarios import _usuarios


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTA
# ──────────────────────────────────────────────────────────────────────────────

def listar_gastos(tipo=None, estado=None):
    g = list(GASTOS_DIRECTOS)
    if tipo:
        g = [x for x in g if x["tipo"] == tipo]
    if estado:
        g = [x for x in g if x["estado"] == estado]
    return g


def obtener_gasto(id_gasto: int):
    return next((g for g in GASTOS_DIRECTOS if g["id_gasto"] == id_gasto), None)


def get_tarjetas():
    return TARJETAS


def get_proveedores():
    return _proveedores


def get_servicios():
    return _servicios


def get_usuarios():
    return _usuarios


def get_analiticas_por_servicio(id_servicio: int):
    return [a for a in _analiticas if a["id_servicio"] == id_servicio]


# ──────────────────────────────────────────────────────────────────────────────
# CREACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def crear_gasto(datos: dict, usuario: dict) -> dict:
    from datetime import datetime
    nuevo_id = max((g["id_gasto"] for g in GASTOS_DIRECTOS), default=0) + 1
    codigo = f"GD-{datetime.now().year}-{nuevo_id:03d}"
    gasto = {
        **datos,
        "id_gasto": nuevo_id,
        "codigo": codigo,
        "estado": "BORRADOR",
        "remesa_directa_id": None,
        "lineas_analitica": [],
        "creado_por": usuario["id_usuario"],
    }
    GASTOS_DIRECTOS.append(gasto)
    return gasto


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO
# ──────────────────────────────────────────────────────────────────────────────

_TRANSICIONES = {
    "BORRADOR":    ["EN_REVISION"],
    "EN_REVISION": ["COTEJADO", "BORRADOR"],
    "COTEJADO":    ["CERRADO"],
}


def actualizar_estado(id_gasto: int, nuevo_estado: str, lineas_analitica=None) -> dict:
    gasto = obtener_gasto(id_gasto)
    if not gasto:
        return {"ok": False, "error": "No encontrado"}
    if nuevo_estado not in _TRANSICIONES.get(gasto["estado"], []):
        return {"ok": False, "error": f"No se puede pasar de {gasto['estado']} a {nuevo_estado}"}
    if nuevo_estado == "COTEJADO":
        if not lineas_analitica:
            return {"ok": False, "error": "Analítica obligatoria para cotejar"}
        if abs(sum(l["porcentaje"] for l in lineas_analitica) - 100) > 0.01:
            return {"ok": False, "error": "Los porcentajes deben sumar 100 %"}
        gasto["lineas_analitica"] = lineas_analitica
    gasto["estado"] = nuevo_estado
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# ANALÍTICAS COMPLETAS
# ──────────────────────────────────────────────────────────────────────────────

def obtener_lineas_analitica(id_gasto: int) -> list:
    gasto = obtener_gasto(id_gasto)
    if not gasto:
        return []
    return [
        {**l, **next((a for a in _analiticas if a["id_analitica"] == l["id_analitica"]), {})}
        for l in gasto.get("lineas_analitica", [])
    ]
