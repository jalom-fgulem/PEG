from typing import List, Dict, Any
from datetime import datetime

_cotejos: List[Dict[str, Any]] = []
_next_id = 1


def crear_cotejo(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id
    nuevo = {
        **datos,
        "id_cotejo": _next_id,
        "fecha_cotejo": datetime.now().strftime("%Y-%m-%d"),
    }
    _cotejos.append(nuevo)
    _next_id += 1
    return nuevo


def obtener_cotejo_por_movimiento(id_movimiento: int) -> Dict[str, Any] | None:
    return next((c for c in _cotejos if c["id_movimiento"] == id_movimiento), None)


def listar_cotejos() -> List[Dict[str, Any]]:
    return list(_cotejos)


def autocotejar_pendientes(movimientos: list, remesas: list) -> int:
    """
    Intenta cotejar automáticamente movimientos PENDIENTE contra remesas.
    Criterio: mismo id_banco + importe del movimiento ≈ suma de pagos de la remesa (±5%).
    Devuelve el número de cotejos realizados.
    """
    from app.services import mock_movimientos
    from app.services.pegs_service import obtener_peg

    realizados = 0
    for mov in movimientos:
        if mov["estado"] != "PENDIENTE":
            continue
        importe_abs = abs(mov["importe"])
        if importe_abs == 0:
            continue

        mejor_remesa = None
        mejor_diff = float("inf")

        for remesa in remesas:
            if remesa.get("id_banco") != mov["id_banco"]:
                continue
            ids_peg = remesa.get("pagos", [])
            pegs = [obtener_peg(pid) for pid in ids_peg]
            pegs = [p for p in pegs if p]
            total_remesa = sum(p.get("importe_total", 0) for p in pegs)
            if total_remesa == 0:
                continue
            diff = abs(total_remesa - importe_abs)
            porcentaje = diff / importe_abs
            if porcentaje <= 0.05 and diff < mejor_diff:
                mejor_diff = diff
                mejor_remesa = remesa

        if mejor_remesa:
            crear_cotejo({
                "id_movimiento": mov["id_movimiento"],
                "tipo_referencia": "REMESA",
                "id_referencia": mejor_remesa["id_remesa"],
                "descripcion": f"Auto-cotejo → {mejor_remesa['codigo_remesa']}",
                "id_usuario": "sistema",
            })
            mock_movimientos.marcar_cotejado(mov["id_movimiento"])
            realizados += 1

    return realizados
