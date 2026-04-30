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


def generar_propuestas_cotejo(movimientos: list, remesas: list) -> list:
    """
    Genera propuestas de cotejo sin ejecutarlas.
    Solo considera gastos (importe < 0) PENDIENTE, nunca ingresos.
    Criterio: mismo id_banco + importe del movimiento ≈ total de la remesa (±5%).
    Devuelve lista de dicts con 'movimiento', 'remesa' y 'diff_pct'.
    Movimientos sin coincidencia se incluyen con remesa=None para que el usuario los vea.
    """
    from app.services.pegs_service import obtener_peg

    ya_cotejados = {c["id_movimiento"] for c in _cotejos}
    propuestas = []

    for mov in movimientos:
        if mov["estado"] != "PENDIENTE":
            continue
        if mov["importe"] >= 0:
            continue  # nunca cotejar ingresos
        if mov["id_movimiento"] in ya_cotejados:
            continue

        importe_abs = abs(mov["importe"])
        mejor_remesa = None
        mejor_diff_pct = float("inf")

        for remesa in remesas:
            if remesa.get("id_banco") != mov["id_banco"]:
                continue
            ids_peg = remesa.get("pagos", [])
            pegs = [obtener_peg(pid) for pid in ids_peg if obtener_peg(pid)]
            total_remesa = sum(p.get("importe_total", 0) for p in pegs)
            if total_remesa == 0:
                continue
            diff_pct = abs(total_remesa - importe_abs) / importe_abs * 100
            if diff_pct <= 5.0 and diff_pct < mejor_diff_pct:
                mejor_diff_pct = diff_pct
                mejor_remesa = remesa

        propuestas.append({
            "movimiento": mov,
            "remesa": mejor_remesa,
            "diff_pct": round(mejor_diff_pct, 2) if mejor_remesa else None,
        })

    return propuestas


def ejecutar_cotejos(confirmados: list, id_usuario: str) -> int:
    """
    Ejecuta cotejos para los pares (id_movimiento, id_remesa) confirmados por el usuario.
    Devuelve el número de cotejos realizados.
    """
    from app.services import mock_movimientos
    from app.services import remesas_service

    realizados = 0
    for par in confirmados:
        id_mov = par["id_movimiento"]
        id_remesa = par["id_remesa"]
        mov = mock_movimientos.obtener_movimiento(id_mov)
        remesa = remesas_service.obtener_remesa(id_remesa)
        if not mov or not remesa:
            continue
        if mov["estado"] != "PENDIENTE":
            continue
        crear_cotejo({
            "id_movimiento": id_mov,
            "tipo_referencia": "REMESA",
            "id_referencia": id_remesa,
            "descripcion": f"Cotejo → {remesa['codigo_remesa']}",
            "id_usuario": id_usuario,
        })
        mock_movimientos.marcar_cotejado(id_mov)
        realizados += 1

    return realizados
