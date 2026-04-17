from app.mock_data import REMESAS_DIRECTAS, GASTOS_DIRECTOS
from app.services.pegs_service import _servicios as SERVICIOS
from app.services.proveedores_service import proveedores_db as _proveedores


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTA
# ──────────────────────────────────────────────────────────────────────────────

def listar_remesas(tipo: str = None):
    r = list(REMESAS_DIRECTAS)
    if tipo:
        r = [x for x in r if x["tipo"] == tipo]
    return r


def obtener_remesa(id_remesa: int):
    return next((r for r in REMESAS_DIRECTAS if r["id_remesa_directa"] == id_remesa), None)


def obtener_gastos_remesa(id_remesa: int) -> list:
    gastos = [g for g in GASTOS_DIRECTOS if g["remesa_directa_id"] == id_remesa]
    proveedores_map = {p["id_proveedor"]: p for p in _proveedores}
    for g in gastos:
        prov = proveedores_map.get(g["proveedor_id"])
        g["nombre_proveedor"] = prov["razon_social"] if prov else "—"
    return gastos


def obtener_gastos_disponibles(tipo_remesa: str) -> list:
    """Gastos COTEJADOS sin remesa asignada y del tipo correspondiente."""
    tipo_gasto = "DOMICILIACION" if tipo_remesa == "DOMICILIACIONES" else "TARJETA"
    gastos = [
        g for g in GASTOS_DIRECTOS
        if g["estado"] == "COTEJADO"
        and g["remesa_directa_id"] is None
        and g["tipo"] == tipo_gasto
    ]
    proveedores_map = {p["id_proveedor"]: p for p in _proveedores}
    for g in gastos:
        prov = proveedores_map.get(g["proveedor_id"])
        g["nombre_proveedor"] = prov["razon_social"] if prov else "—"
    return gastos


def totales_remesa(id_remesa: int) -> dict:
    gastos = [g for g in GASTOS_DIRECTOS if g["remesa_directa_id"] == id_remesa]
    return {
        "num_gastos": len(gastos),
        "total_base": sum(g["importe_base"] for g in gastos),
        "total_iva":  sum(g["importe_iva"]  for g in gastos),
        "total":      sum(g["importe_total"] for g in gastos),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CREACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def crear_remesa(datos: dict) -> dict:
    from datetime import datetime
    nuevo_id = max((r["id_remesa_directa"] for r in REMESAS_DIRECTAS), default=0) + 1
    numero   = max((r["numero"]            for r in REMESAS_DIRECTAS), default=0) + 1
    remesa = {
        **datos,
        "id_remesa_directa": nuevo_id,
        "numero": numero,
        "estado": "ABIERTA",
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "fecha_cierre": None,
    }
    REMESAS_DIRECTAS.append(remesa)
    return remesa


# ──────────────────────────────────────────────────────────────────────────────
# OPERACIONES
# ──────────────────────────────────────────────────────────────────────────────

def añadir_gasto(id_remesa: int, id_gasto: int) -> dict:
    remesa = obtener_remesa(id_remesa)
    gasto  = next((g for g in GASTOS_DIRECTOS if g["id_gasto"] == id_gasto), None)
    if not remesa or not gasto:
        return {"ok": False, "error": "No encontrado"}
    if remesa["estado"] != "ABIERTA":
        return {"ok": False, "error": "La remesa no está abierta"}
    if gasto["estado"] != "COTEJADO":
        return {"ok": False, "error": "El gasto no está cotejado"}
    gasto["remesa_directa_id"] = id_remesa
    return {"ok": True}


def quitar_gasto(id_remesa: int, id_gasto: int) -> dict:
    gasto = next((g for g in GASTOS_DIRECTOS if g["id_gasto"] == id_gasto), None)
    if not gasto:
        return {"ok": False, "error": "Gasto no encontrado"}
    gasto["remesa_directa_id"] = None
    return {"ok": True}


def cerrar_remesa(id_remesa: int) -> dict:
    from datetime import datetime
    remesa = obtener_remesa(id_remesa)
    if not remesa:
        return {"ok": False, "error": "Remesa no encontrada"}
    gastos = [g for g in GASTOS_DIRECTOS if g["remesa_directa_id"] == id_remesa]
    if not gastos:
        return {"ok": False, "error": "No hay gastos asignados a esta remesa"}
    for g in gastos:
        g["estado"] = "CERRADO"
    remesa["estado"] = "CERRADA"
    remesa["fecha_cierre"] = datetime.now().strftime("%Y-%m-%d")
    return {"ok": True}
