from decimal import Decimal
from datetime import date, datetime
from typing import Optional

from app.mock_data import SOLICITUDES_AUTORIZACION
import app.mock_data as _md
from app.services.mock_servicios import obtener_servicio
from app.services.proveedores_service import obtener_proveedor
from app.services.mock_usuarios import obtener_usuario


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de enriquecimiento
# ──────────────────────────────────────────────────────────────────────────────

def _enriquecer(s: dict) -> dict:
    out = dict(s)
    proveedor = obtener_proveedor(s["id_proveedor"])
    servicio  = obtener_servicio(s["id_servicio"])
    solicitante = obtener_usuario(s["id_usuario_solicitante"])
    autorizador = obtener_usuario(s["id_usuario_autorizador"]) if s.get("id_usuario_autorizador") else None

    out["nombre_proveedor"]    = proveedor["razon_social"] if proveedor else "—"
    out["nombre_servicio"]     = servicio["nombre"]        if servicio  else "—"
    out["nombre_solicitante"]  = solicitante["nombre_completo"] if solicitante else "—"
    out["nombre_autorizador"]  = autorizador["nombre_completo"] if autorizador else None

    # Badge CSS class
    _badge = {
        "PENDIENTE_AUTORIZACION": "pendiente",
        "AUTORIZADA":             "autorizada",
        "DENEGADA":               "denegada",
    }
    out["badge_clase"] = _badge.get(s["estado"], "pendiente")

    # Adjuntos como lista limpia
    out["adjuntos"] = [
        s[k] for k in ("adjunto_1", "adjunto_2", "adjunto_3") if s.get(k)
    ]
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Consultas
# ──────────────────────────────────────────────────────────────────────────────

def listar_solicitudes(id_servicio: Optional[int] = None) -> list[dict]:
    items = SOLICITUDES_AUTORIZACION
    if id_servicio is not None:
        items = [s for s in items if s["id_servicio"] == id_servicio]
    return [_enriquecer(s) for s in items]


def obtener_solicitud(id_solicitud: int) -> Optional[dict]:
    raw = next((s for s in SOLICITUDES_AUTORIZACION if s["id_solicitud"] == id_solicitud), None)
    return _enriquecer(raw) if raw else None


def obtener_solicitud_raw(id_solicitud: int) -> Optional[dict]:
    return next((s for s in SOLICITUDES_AUTORIZACION if s["id_solicitud"] == id_solicitud), None)


# ──────────────────────────────────────────────────────────────────────────────
# Creación
# ──────────────────────────────────────────────────────────────────────────────

def crear_solicitud(
    id_servicio: int,
    id_usuario_solicitante: int,
    id_proveedor: int,
    importe_estimado: Decimal,
    concepto: str,
    fecha_estimada_gasto: date,
    adjunto_1: Optional[str] = None,
    adjunto_2: Optional[str] = None,
    adjunto_3: Optional[str] = None,
) -> dict:
    servicio = obtener_servicio(id_servicio)
    if not servicio or not servicio.get("requiere_autorizacion"):
        raise ValueError("El servicio no requiere autorización previa")

    nueva = {
        "id_solicitud":          _md._next_solicitud_id,
        "id_servicio":           id_servicio,
        "id_usuario_solicitante": id_usuario_solicitante,
        "id_proveedor":          id_proveedor,
        "importe_estimado":      importe_estimado,
        "concepto":              concepto,
        "fecha_estimada_gasto":  fecha_estimada_gasto,
        "adjunto_1":             adjunto_1,
        "adjunto_2":             adjunto_2,
        "adjunto_3":             adjunto_3,
        "estado":                "PENDIENTE_AUTORIZACION",
        "id_usuario_autorizador": None,
        "fecha_resolucion":      None,
        "motivo_denegacion":     None,
        "id_peg_generado":       None,
        "fecha_creacion":        datetime.now(),
    }
    _md._next_solicitud_id += 1
    SOLICITUDES_AUTORIZACION.append(nueva)
    return _enriquecer(nueva)


# ──────────────────────────────────────────────────────────────────────────────
# Resolución
# ──────────────────────────────────────────────────────────────────────────────

def autorizar(id_solicitud: int, id_usuario_autorizador: int) -> dict | None:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado"] != "PENDIENTE_AUTORIZACION":
        return None
    raw["estado"]                = "AUTORIZADA"
    raw["id_usuario_autorizador"] = id_usuario_autorizador
    raw["fecha_resolucion"]      = datetime.now()
    raw["motivo_denegacion"]     = None
    return _enriquecer(raw)


def denegar(id_solicitud: int, id_usuario_autorizador: int, motivo: str) -> dict | None:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado"] != "PENDIENTE_AUTORIZACION":
        return None
    raw["estado"]                = "DENEGADA"
    raw["id_usuario_autorizador"] = id_usuario_autorizador
    raw["fecha_resolucion"]      = datetime.now()
    raw["motivo_denegacion"]     = motivo.strip()
    return _enriquecer(raw)


# ──────────────────────────────────────────────────────────────────────────────
# Vincular PEG generado
# ──────────────────────────────────────────────────────────────────────────────

def vincular_peg(id_solicitud: int, id_peg: int) -> bool:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado"] != "AUTORIZADA":
        return False
    raw["id_peg_generado"] = id_peg
    return True
