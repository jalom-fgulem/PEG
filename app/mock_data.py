from decimal import Decimal
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Solicitudes de autorización previas al gasto (solo servicios con
# requiere_autorizacion=True, actualmente Hospital Veterinario Universitario).
# ---------------------------------------------------------------------------
SOLICITUDES_AUTORIZACION: list[dict] = [
    {
        "id_solicitud": 1,
        "id_servicio": 1,
        "id_usuario_solicitante": 1,       # Gestor HVU
        "id_proveedor": 3,                 # Veterinaria Técnica del Noroeste SL
        "importe_estimado": Decimal("1250.00"),
        "concepto": "Material quirúrgico desechable — reposición trimestral",
        "fecha_estimada_gasto": date(2026, 4, 30),
        "adjunto_1": "media/autorizaciones/1/presupuesto_material.pdf",
        "adjunto_2": None,
        "adjunto_3": None,
        "estado": "PENDIENTE_AUTORIZACION",
        "id_usuario_autorizador": None,
        "fecha_resolucion": None,
        "motivo_denegacion": None,
        "id_peg_generado": None,
        "fecha_creacion": datetime(2026, 4, 14, 9, 15, 0),
    },
    {
        "id_solicitud": 2,
        "id_servicio": 1,
        "id_usuario_solicitante": 1,       # Gestor HVU
        "id_proveedor": 1,                 # Proveedor Ejemplo SL
        "importe_estimado": Decimal("480.50"),
        "concepto": "Servicio de mantenimiento equipos diagnóstico — febrero 2026",
        "fecha_estimada_gasto": date(2026, 3, 15),
        "adjunto_1": "media/autorizaciones/2/presupuesto_mantenimiento.pdf",
        "adjunto_2": "media/autorizaciones/2/contrato_marco.pdf",
        "adjunto_3": None,
        "estado": "AUTORIZADA",
        "id_usuario_autorizador": 3,       # Gestor Económico FGULEM
        "fecha_resolucion": datetime(2026, 3, 10, 11, 42, 0),
        "motivo_denegacion": None,
        "id_peg_generado": None,           # Autorizada pero PEG aún no creado
        "fecha_creacion": datetime(2026, 3, 8, 16, 5, 0),
    },
    {
        "id_solicitud": 3,
        "id_servicio": 1,
        "id_usuario_solicitante": 1,       # Gestor HVU
        "id_proveedor": 3,                 # Veterinaria Técnica del Noroeste SL
        "importe_estimado": Decimal("3900.00"),
        "concepto": "Adquisición analizador hematológico portátil",
        "fecha_estimada_gasto": date(2026, 2, 28),
        "adjunto_1": "media/autorizaciones/3/oferta_analizador.pdf",
        "adjunto_2": None,
        "adjunto_3": None,
        "estado": "DENEGADA",
        "id_usuario_autorizador": 3,       # Gestor Económico FGULEM
        "fecha_resolucion": datetime(2026, 2, 20, 9, 0, 0),
        "motivo_denegacion": (
            "Importe supera el límite de gasto autorizado para este trimestre. "
            "Se solicita aplazar la adquisición al ejercicio siguiente."
        ),
        "id_peg_generado": None,
        "fecha_creacion": datetime(2026, 2, 18, 14, 30, 0),
    },
]

_next_solicitud_id = 4

# ---------------------------------------------------------------------------
# Adjuntos de PEGs almacenados en Drive.
# En producción esta lista será reemplazada por una tabla en BD.
peg_adjuntos: list[dict] = [
    {
        "id_documento": 1,
        "id_peg": 1,
        "tipo": "FACTURA",
        "nombre_archivo": "factura_veterinaria_001.pdf",
        "ruta": "media/pegs/1/factura_veterinaria_001.pdf",
        "fecha_subida": "2026-01-20",
    },
    {
        "id_documento": 2,
        "id_peg": 2,
        "tipo": "PRESUPUESTO",
        "nombre_archivo": "presupuesto_idiomas.jpg",
        "ruta": "media/pegs/2/presupuesto_idiomas.jpg",
        "fecha_subida": "2026-02-10",
    },
]

_next_adj_id = 3


def next_adj_id() -> int:
    global _next_adj_id
    current = _next_adj_id
    _next_adj_id += 1
    return current


def siguiente_cuenta_cliente() -> str:
    """
    Calcula la siguiente cuenta cliente disponible del grupo 4.
    Busca el máximo numérico entre todas las cuentas cliente
    de todos los proveedores y devuelve el siguiente.
    Base: 4100001
    """
    from app.services.proveedores_service import proveedores_db as PROVEEDORES
    BASE = 4100001
    maximo = BASE - 1
    for p in PROVEEDORES:
        cuenta = p.get("cuenta_cliente", "")
        if cuenta and cuenta.isdigit():
            val = int(cuenta)
            if val > maximo:
                maximo = val
    return str(maximo + 1)
