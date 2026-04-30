from typing import List, Dict, Any
from datetime import datetime

_movimientos: List[Dict[str, Any]] = [
    {
        "id_mov_tarjeta": 1,
        "id_tarjeta": 1,
        "fecha_operacion": "2026-04-03",
        "fecha_valor": "2026-04-05",
        "concepto": "EL CORTE INGLES LEON MATERIAL OFICINA",
        "importe": -89.50,
        "referencia": "VISA-2026-0001",
        "estado": "PENDIENTE",
        "fecha_importacion": "2026-04-15",
        "id_usuario_importa": "admin",
    },
    {
        "id_mov_tarjeta": 2,
        "id_tarjeta": 1,
        "fecha_operacion": "2026-04-07",
        "fecha_valor": "2026-04-09",
        "concepto": "AMAZON MARKETPLACE MATERIAL INFORMATICO",
        "importe": -134.99,
        "referencia": "VISA-2026-0002",
        "estado": "PENDIENTE",
        "fecha_importacion": "2026-04-15",
        "id_usuario_importa": "admin",
    },
    {
        "id_mov_tarjeta": 3,
        "id_tarjeta": 1,
        "fecha_operacion": "2026-04-12",
        "fecha_valor": "2026-04-14",
        "concepto": "RENFE BILLETE TREN MADRID-LEON",
        "importe": -42.30,
        "referencia": "VISA-2026-0003",
        "estado": "PENDIENTE",
        "fecha_importacion": "2026-04-15",
        "id_usuario_importa": "admin",
    },
    {
        "id_mov_tarjeta": 4,
        "id_tarjeta": 2,
        "fecha_operacion": "2026-04-05",
        "fecha_valor": "2026-04-07",
        "concepto": "HOTEL MELIA MADRID CONGRESO",
        "importe": -187.00,
        "referencia": "MC-2026-0001",
        "estado": "PENDIENTE",
        "fecha_importacion": "2026-04-16",
        "id_usuario_importa": "admin",
    },
    {
        "id_mov_tarjeta": 5,
        "id_tarjeta": 2,
        "fecha_operacion": "2026-04-15",
        "fecha_valor": "2026-04-17",
        "concepto": "IBERIA EXPRESS VUELO MADRID-BARCELONA",
        "importe": -89.90,
        "referencia": "MC-2026-0002",
        "estado": "PENDIENTE",
        "fecha_importacion": "2026-04-16",
        "id_usuario_importa": "admin",
    },
]

_next_id = 6

_cotejos: List[Dict[str, Any]] = []
_next_cotejo_id = 1


def listar_movimientos(
    id_tarjeta: int | None = None,
    estado: str | None = None,
) -> List[Dict[str, Any]]:
    result = list(_movimientos)
    if id_tarjeta:
        result = [m for m in result if m["id_tarjeta"] == id_tarjeta]
    if estado:
        result = [m for m in result if m["estado"] == estado]
    return sorted(result, key=lambda m: m["fecha_operacion"], reverse=True)


def obtener_movimiento(id_mov_tarjeta: int) -> Dict[str, Any] | None:
    return next((m for m in _movimientos if m["id_mov_tarjeta"] == id_mov_tarjeta), None)


def crear_movimiento(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id
    nuevo = {**datos, "id_mov_tarjeta": _next_id, "fecha_importacion": datetime.now().strftime("%Y-%m-%d")}
    _movimientos.append(nuevo)
    _next_id += 1
    return nuevo


def marcar_ignorado(id_mov_tarjeta: int) -> bool:
    mov = obtener_movimiento(id_mov_tarjeta)
    if not mov:
        return False
    mov["estado"] = "IGNORADO"
    return True


def marcar_cotejado(id_mov_tarjeta: int) -> bool:
    mov = obtener_movimiento(id_mov_tarjeta)
    if not mov:
        return False
    mov["estado"] = "COTEJADO"
    return True


def existe_referencia(referencia: str, id_tarjeta: int) -> bool:
    return any(m["referencia"] == referencia and m["id_tarjeta"] == id_tarjeta for m in _movimientos)


# ── Cotejos ───────────────────────────────────────────────────────────────────

def crear_cotejo(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_cotejo_id
    nuevo = {**datos, "id_cotejo": _next_cotejo_id}
    _cotejos.append(nuevo)
    _next_cotejo_id += 1
    return nuevo


def obtener_cotejo(id_mov_tarjeta: int) -> Dict[str, Any] | None:
    return next((c for c in _cotejos if c["id_mov_tarjeta"] == id_mov_tarjeta), None)


def listar_cotejos() -> List[Dict[str, Any]]:
    return list(_cotejos)
