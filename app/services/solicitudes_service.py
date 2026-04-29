from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List

from app.mock_data import SOLICITUDES_AUTORIZACION, solicitud_adjuntos
import app.mock_data as _md
from app.services.mock_servicios import obtener_servicio
from app.services.proveedores_service import obtener_proveedor
from app.services.mock_usuarios import obtener_usuario


# ── Tipos de adjunto ───────────────────────────────────────────────────────────
_TIPOS_ADJ = {
    "PRESUPUESTO":     "Presupuesto",
    "FACTURA_PROFORMA": "Factura proforma",
    "OTRO":            "Documento adicional",
}


# ── Helpers de enriquecimiento ─────────────────────────────────────────────────

def _enriquecer(s: dict) -> dict:
    out = dict(s)
    proveedor   = obtener_proveedor(s["id_proveedor"])
    servicio    = obtener_servicio(s["id_servicio"])
    solicitante = obtener_usuario(s["id_usuario_solicitante"])
    autorizador = obtener_usuario(s["id_usuario_autorizador"]) if s.get("id_usuario_autorizador") else None

    out["nombre_proveedor"]   = proveedor["razon_social"] if proveedor else "—"
    out["nombre_servicio"]    = servicio["nombre"]        if servicio  else "—"
    out["nombre_solicitante"] = solicitante["nombre_completo"] if solicitante else "—"
    out["nombre_autorizador"] = autorizador["nombre_completo"] if autorizador else None

    _badge = {
        "PENDIENTE_AUTORIZACION": "pendiente",
        "AUTORIZADA":             "autorizada",
        "DENEGADA":               "denegada",
    }
    out["badge_clase"] = _badge.get(s["estado_solicitud"], "pendiente")

    # Adjuntos del registro separado
    docs = [a for a in solicitud_adjuntos if a["id_solicitud"] == s["id_solicitud"]]
    out["documentos"] = docs
    # También exponer lista de rutas para compatibilidad con plantilla antigua
    out["adjuntos"] = [a["ruta"] for a in docs]

    return out


# ── Consultas ──────────────────────────────────────────────────────────────────

def listar_solicitudes(
    id_servicio: Optional[int] = None,
    estado: Optional[str] = None,
) -> list[dict]:
    # Normalizar alias cortos: PENDIENTE → PENDIENTE_AUTORIZACION
    _alias = {"PENDIENTE": "PENDIENTE_AUTORIZACION"}
    estado_norm = _alias.get(estado, estado) if estado else None

    items = SOLICITUDES_AUTORIZACION
    if id_servicio is not None:
        items = [s for s in items if s["id_servicio"] == id_servicio]
    if estado_norm:
        items = [s for s in items if s.get("estado_solicitud") == estado_norm]
    return [_enriquecer(s) for s in items]


def obtener_solicitud(id_solicitud: int) -> Optional[dict]:
    raw = next((s for s in SOLICITUDES_AUTORIZACION if s["id_solicitud"] == id_solicitud), None)
    return _enriquecer(raw) if raw else None


def obtener_solicitud_raw(id_solicitud: int) -> Optional[dict]:
    return next((s for s in SOLICITUDES_AUTORIZACION if s["id_solicitud"] == id_solicitud), None)


# ── Creación ───────────────────────────────────────────────────────────────────

def crear_solicitud(
    id_servicio: int,
    id_usuario_solicitante: int,
    id_proveedor: int,
    importe_estimado: Decimal,
    concepto: str,
    fecha_estimada_gasto: date,
    lineas: Optional[List[dict]] = None,
    base_imponible: float = 0.0,
    importe_iva: float = 0.0,
    importe_irpf: float = 0.0,
    tiene_irpf: bool = False,
    tipo_irpf: float = 0.0,
    id_forma_pago: int = 1,
) -> dict:
    servicio = obtener_servicio(id_servicio)
    if not servicio:
        raise ValueError("Servicio no encontrado")

    nueva = {
        "id_solicitud":           _md._next_solicitud_id,
        "id_servicio":            id_servicio,
        "id_usuario_solicitante": id_usuario_solicitante,
        "id_proveedor":           id_proveedor,
        "importe_estimado":       importe_estimado,
        "concepto":               concepto,
        "fecha_estimada_gasto":   fecha_estimada_gasto,
        "lineas":                 lineas or [],
        "base_imponible":         base_imponible,
        "importe_iva":            importe_iva,
        "importe_irpf":           importe_irpf,
        "tiene_irpf":             tiene_irpf,
        "tipo_irpf":              tipo_irpf,
        "id_forma_pago":          id_forma_pago,
        "estado_solicitud":       "PENDIENTE_AUTORIZACION",
        "id_usuario_autorizador": None,
        "fecha_resolucion":       None,
        "motivo_denegacion":      None,
        "id_peg_generado":        None,
        "fecha_creacion":         datetime.now(),
    }
    _md._next_solicitud_id += 1
    SOLICITUDES_AUTORIZACION.append(nueva)
    return _enriquecer(nueva)


# ── Adjuntos ───────────────────────────────────────────────────────────────────

def adjuntar_doc(id_solicitud: int, nombre_archivo: str, ruta: str, tipo: str) -> dict:
    doc = {
        "id_sol_adj":    _md.next_sol_adj_id(),
        "id_solicitud":  id_solicitud,
        "tipo":          tipo,
        "nombre_archivo": nombre_archivo,
        "ruta":          ruta,
        "fecha_subida":  datetime.now().strftime("%Y-%m-%d"),
    }
    solicitud_adjuntos.append(doc)
    return doc


def obtener_doc(id_solicitud: int, id_sol_adj: int) -> dict | None:
    return next(
        (a for a in solicitud_adjuntos
         if a["id_sol_adj"] == id_sol_adj and a["id_solicitud"] == id_solicitud),
        None,
    )


def eliminar_doc(id_solicitud: int, id_sol_adj: int) -> bool:
    doc = next(
        (a for a in solicitud_adjuntos
         if a["id_sol_adj"] == id_sol_adj and a["id_solicitud"] == id_solicitud),
        None,
    )
    if not doc:
        return False
    solicitud_adjuntos.remove(doc)
    return True


# ── Resolución ─────────────────────────────────────────────────────────────────

def autorizar(id_solicitud: int, id_usuario_autorizador: int) -> dict | None:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado_solicitud"] != "PENDIENTE_AUTORIZACION":
        return None
    raw["estado_solicitud"]       = "AUTORIZADA"
    raw["id_usuario_autorizador"] = id_usuario_autorizador
    raw["fecha_resolucion"]       = datetime.now()
    raw["motivo_denegacion"]      = None
    return _enriquecer(raw)


def denegar(id_solicitud: int, id_usuario_autorizador: int, motivo: str) -> dict | None:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado_solicitud"] != "PENDIENTE_AUTORIZACION":
        return None
    raw["estado_solicitud"]       = "DENEGADA"
    raw["id_usuario_autorizador"] = id_usuario_autorizador
    raw["fecha_resolucion"]       = datetime.now()
    raw["motivo_denegacion"]      = motivo.strip()
    return _enriquecer(raw)


# ── Vincular PEG generado ──────────────────────────────────────────────────────

def vincular_peg(id_solicitud: int, id_peg: int) -> bool:
    raw = obtener_solicitud_raw(id_solicitud)
    if not raw or raw["estado_solicitud"] != "AUTORIZADA":
        return False
    raw["id_peg_generado"] = id_peg
    return True
