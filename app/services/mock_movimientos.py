from typing import List, Dict, Any
from datetime import datetime

_movimientos: List[Dict[str, Any]] = [
    {
        "id_movimiento": 1,
        "id_banco": 1,
        "fecha_operacion": "2026-04-01",
        "fecha_valor": "2026-04-01",
        "concepto": "REMESA TRANSFERENCIAS MARZO 2026",
        "importe": -12450.00,
        "saldo_posterior": 87550.00,
        "referencia_banco": "REF20260401001",
        "tipo": "TRANSFERENCIA",
        "estado": "PENDIENTE",
        "origen": "FICHERO_MT940",
        "fecha_importacion": "2026-04-10",
        "id_usuario_importa": "admin",
    },
    {
        "id_movimiento": 2,
        "id_banco": 1,
        "fecha_operacion": "2026-04-05",
        "fecha_valor": "2026-04-05",
        "concepto": "ENDESA SUMINISTRO ELECTRICO MARZO",
        "importe": -380.00,
        "saldo_posterior": 87170.00,
        "referencia_banco": "REF20260405001",
        "tipo": "DOMICILIACION",
        "estado": "PENDIENTE",
        "origen": "FICHERO_MT940",
        "fecha_importacion": "2026-04-10",
        "id_usuario_importa": "admin",
    },
    {
        "id_movimiento": 3,
        "id_banco": 1,
        "fecha_operacion": "2026-04-08",
        "fecha_valor": "2026-04-08",
        "concepto": "COMISION MANTENIMIENTO CUENTA ABRIL",
        "importe": -12.50,
        "saldo_posterior": 87157.50,
        "referencia_banco": "REF20260408001",
        "tipo": "COMISION",
        "estado": "PENDIENTE",
        "origen": "FICHERO_MT940",
        "fecha_importacion": "2026-04-10",
        "id_usuario_importa": "admin",
    },
    {
        "id_movimiento": 4,
        "id_banco": 2,
        "fecha_operacion": "2026-04-10",
        "fecha_valor": "2026-04-10",
        "concepto": "TRANSFERENCIA RECIBIDA ULE SUBVENCION",
        "importe": 5000.00,
        "saldo_posterior": 25000.00,
        "referencia_banco": "REF20260410001",
        "tipo": "TRANSFERENCIA",
        "estado": "PENDIENTE",
        "origen": "FICHERO_CSV",
        "fecha_importacion": "2026-04-15",
        "id_usuario_importa": "admin",
    },
]

_next_id = 5


def listar_movimientos(
    id_banco: int | None = None,
    estado: str | None = None,
    tipo: str | None = None,
) -> List[Dict[str, Any]]:
    result = list(_movimientos)
    if id_banco:
        result = [m for m in result if m["id_banco"] == id_banco]
    if estado:
        result = [m for m in result if m["estado"] == estado]
    if tipo:
        result = [m for m in result if m["tipo"] == tipo]
    return sorted(result, key=lambda m: m["fecha_operacion"], reverse=True)


def obtener_movimiento(id_movimiento: int) -> Dict[str, Any] | None:
    return next((m for m in _movimientos if m["id_movimiento"] == id_movimiento), None)


def crear_movimiento(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id
    nuevo = {**datos, "id_movimiento": _next_id, "fecha_importacion": datetime.now().strftime("%Y-%m-%d")}
    _movimientos.append(nuevo)
    _next_id += 1
    return nuevo


def marcar_ignorado(id_movimiento: int) -> bool:
    mov = obtener_movimiento(id_movimiento)
    if not mov:
        return False
    mov["estado"] = "IGNORADO"
    return True


def marcar_cotejado(id_movimiento: int) -> bool:
    mov = obtener_movimiento(id_movimiento)
    if not mov:
        return False
    mov["estado"] = "COTEJADO"
    return True


def existe_referencia(referencia_banco: str, id_banco: int) -> bool:
    return any(
        m["referencia_banco"] == referencia_banco and m["id_banco"] == id_banco
        for m in _movimientos
    )
