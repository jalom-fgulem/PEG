from datetime import datetime
from app.services import mock_bancos

# ──────────────────────────────────────────────────────────────────────────────
# DATOS SIMULADOS EN MEMORIA (sustituir por BD real cuando esté disponible)
# Estados válidos: "ABIERTA", "GENERADA", "CERRADA"
# ──────────────────────────────────────────────────────────────────────────────

_remesas = [
    {
        "id_remesa": 1,
        "codigo_remesa": "REM-2026-0001",
        "descripcion": "Remesa enero 2026 - Hospital Veterinario",
        "fecha_creacion": "2026-01-20",
        "fecha_cierre": None,
        "estado": "ABIERTA",
        "pdf_path": None,
        "id_servicio": 1,
        "id_banco": 1,
        "creado_por": "José Carlos Alonso",
        "pagos": [1],  # id_peg incluidos
    },
    {
        "id_remesa": 2,
        "codigo_remesa": "REM-2026-0002",
        "descripcion": "Remesa febrero 2026 - Centro de Idiomas",
        "fecha_creacion": "2026-02-28",
        "fecha_cierre": "2026-03-01",
        "estado": "GENERADA",
        "pdf_path": "media/remesas/remesa_2_20260301.pdf",
        "id_servicio": 2,
        "id_banco": 1,
        "creado_por": "José Carlos Alonso",
        "pagos": [2, 3],
    },
    {
        "id_remesa": 3,
        "codigo_remesa": "REM-2026-0003",
        "descripcion": "Remesa marzo 2026 - Desarrollo Profesional",
        "fecha_creacion": "2026-03-15",
        "fecha_cierre": "2026-03-20",
        "estado": "CERRADA",
        "pdf_path": "media/remesas/remesa_3_20260320.pdf",
        "id_servicio": 3,
        "id_banco": 1,
        "creado_por": "José Carlos Alonso",
        "pagos": [4],
    },
]

_siguiente_id = 4


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

def listar_remesas(estado: str | None = None, id_servicio: int | None = None) -> list[dict]:
    resultado = []
    for r in _remesas:
        if estado and r["estado"] != estado:
            continue
        if id_servicio and r["id_servicio"] != id_servicio:
            continue
        resultado.append(r)
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────────────────────────────────────

def obtener_remesa(id_remesa: int) -> dict | None:
    return next((r for r in _remesas if r["id_remesa"] == id_remesa), None)


# ──────────────────────────────────────────────────────────────────────────────
# CREACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def crear_remesa(descripcion: str, id_servicio: int, creado_por: str = "Usuario", id_banco: int = 1) -> dict:
    global _siguiente_id
    anio = datetime.now().year
    num = sum(1 for r in _remesas if r["codigo_remesa"].startswith(f"REM-{anio}")) + 1
    nueva = {
        "id_remesa": _siguiente_id,
        "codigo_remesa": f"REM-{anio}-{num:04d}",
        "descripcion": descripcion,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "fecha_cierre": None,
        "estado": "ABIERTA",
        "pdf_path": None,
        "id_servicio": id_servicio,
        "id_banco": id_banco,
        "creado_por": creado_por,
        "pagos": [],
    }
    _remesas.append(nueva)
    _siguiente_id += 1
    return nueva


# ──────────────────────────────────────────────────────────────────────────────
# ELIMINAR REMESA
# ──────────────────────────────────────────────────────────────────────────────

def eliminar_remesa(id_remesa: int) -> bool:
    remesa = obtener_remesa(id_remesa)
    if not remesa or remesa["estado"] != "ABIERTA":
        return False
    _remesas.remove(remesa)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# AÑADIR / QUITAR PAGOS
# ──────────────────────────────────────────────────────────────────────────────

def añadir_pago(id_remesa: int, id_peg: int) -> bool:
    remesa = obtener_remesa(id_remesa)
    if not remesa or remesa["estado"] != "ABIERTA":
        return False
    if id_peg not in remesa["pagos"]:
        remesa["pagos"].append(id_peg)
    from app.services import pegs_service
    peg = pegs_service.get_peg_raw(id_peg)
    if peg is not None:
        peg["id_remesa"] = id_remesa
    return True


def quitar_pago(id_remesa: int, id_peg: int) -> bool:
    remesa = obtener_remesa(id_remesa)
    if not remesa or remesa["estado"] != "ABIERTA":
        return False
    if id_peg in remesa["pagos"]:
        remesa["pagos"].remove(id_peg)
    from app.services import pegs_service
    peg = pegs_service.get_peg_raw(id_peg)
    if peg is not None:
        peg["id_remesa"] = None
    return True


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO
# ──────────────────────────────────────────────────────────────────────────────

_TRANSICIONES_VALIDAS = {
    "ABIERTA":  ["GENERADA"],
    "GENERADA": ["CERRADA"],
    "CERRADA":  [],
}


def cambiar_estado_remesa(id_remesa: int, nuevo_estado: str) -> dict | None:
    """Devuelve la remesa actualizada o None si la transición no es válida."""
    remesa = obtener_remesa(id_remesa)
    if not remesa:
        return None
    if nuevo_estado not in _TRANSICIONES_VALIDAS.get(remesa["estado"], []):
        return None
    remesa["estado"] = nuevo_estado
    if nuevo_estado == "CERRADA":
        remesa["fecha_cierre"] = datetime.now().strftime("%Y-%m-%d")
    return remesa


# ──────────────────────────────────────────────────────────────────────────────
# ACTUALIZAR PDF PATH
# ──────────────────────────────────────────────────────────────────────────────

def actualizar_pdf_path(id_remesa: int, pdf_path: str) -> bool:
    remesa = obtener_remesa(id_remesa)
    if not remesa:
        return False
    remesa["pdf_path"] = pdf_path
    return True
