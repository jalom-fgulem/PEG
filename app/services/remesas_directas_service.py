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


def obtener_gastos_disponibles() -> list:
    """Gastos COTEJADOS sin remesa asignada."""
    gastos = [
        g for g in GASTOS_DIRECTOS
        if g["estado"] == "COTEJADO"
        and g["remesa_directa_id"] is None
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
        "descripcion":      datos.get("descripcion", ""),
        "cuenta_bancaria_id": datos.get("cuenta_bancaria_id"),
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
    prov = next((p for p in _proveedores if p["id_proveedor"] == gasto.get("proveedor_id")), None)
    if prov and not prov.get("cuenta_cliente"):
        return {
            "ok": False,
            "error": f"No se puede remesar: el proveedor «{prov['razon_social']}» "
                     "no tiene asignada la cuenta contable de acreedor (grupo 4). "
                     "Asígnala en la ficha del proveedor antes de incluirlo en la remesa."
        }
    gasto["remesa_directa_id"] = id_remesa
    return {"ok": True}


def quitar_gasto(id_remesa: int, id_gasto: int) -> dict:
    gasto = next((g for g in GASTOS_DIRECTOS if g["id_gasto"] == id_gasto), None)
    if not gasto:
        return {"ok": False, "error": "Gasto no encontrado"}
    gasto["remesa_directa_id"] = None
    return {"ok": True}


def crear_gasto_desde_movimiento(id_remesa: int, mov: dict, tipo_gasto: str,
                                  cuenta_gasto: str, proveedor_id,
                                  lineas_analitica: list) -> dict:
    """Crea un GASTO_DIRECTO a partir de un movimiento bancario y lo vincula a una remesa abierta."""
    from datetime import datetime
    remesa = obtener_remesa(id_remesa)
    if not remesa:
        return {"ok": False, "error": "Remesa no encontrada"}
    if remesa["estado"] != "ABIERTA":
        return {"ok": False, "error": "La remesa no está abierta"}

    nuevo_id = max((g["id_gasto"] for g in GASTOS_DIRECTOS), default=0) + 1
    n = nuevo_id
    anno = datetime.now().year
    codigo = f"GD-{anno}-MOV{n:04d}"
    importe = abs(mov.get("importe", 0.0))

    try:
        prov_id = int(proveedor_id) if proveedor_id else None
    except (ValueError, TypeError):
        prov_id = None

    gasto = {
        "id_gasto": nuevo_id,
        "codigo": codigo,
        "tipo": tipo_gasto,
        "proveedor_id": prov_id,
        "tarjeta_id": None,
        "empleado_id": None,
        "fecha_documento": mov.get("fecha_operacion", datetime.now().strftime("%Y-%m-%d")),
        "fecha_cargo_real": mov.get("fecha_valor", mov.get("fecha_operacion", datetime.now().strftime("%Y-%m-%d"))),
        "importe_base": round(importe, 2),
        "importe_iva": 0.0,
        "importe_total": round(importe, 2),
        "irpf": 0.0,
        "referencia_factura": mov.get("referencia", ""),
        "concepto": mov.get("concepto", ""),
        "cuenta_gasto": cuenta_gasto,
        "estado": "COTEJADO",
        "remesa_directa_id": id_remesa,
        "servicio_id": None,
        "lineas_analitica": lineas_analitica,
        "lineas_iva": [],
        "id_movimiento_origen": mov.get("id_movimiento"),
    }
    GASTOS_DIRECTOS.append(gasto)
    return {"ok": True, "id_gasto": nuevo_id, "codigo": codigo}


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
