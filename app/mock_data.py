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


TARJETAS: list[dict] = [
    {"id_tarjeta": 1, "nombre": "Visa FGULEM Principal",
     "ultimos_4": "4521", "titular_defecto_id": 1, "activa": True},
    {"id_tarjeta": 2, "nombre": "Visa FGULEM Secundaria",
     "ultimos_4": "8834", "titular_defecto_id": 1, "activa": True},
]

GASTOS_DIRECTOS: list[dict] = [
    {"id_gasto": 1, "codigo": "GD-2026-001",
     "tipo": "DOMICILIACION",
     "proveedor_id": 1,
     "tarjeta_id": None, "empleado_id": None,
     "fecha_documento": "2026-03-01",
     "fecha_cargo_real": "2026-03-03",
     "importe_base": 850.00, "importe_iva": 178.50, "importe_total": 1028.50,
     "irpf": 0.0,
     "referencia_factura": "F-2026-0123",
     "concepto": "Servicio mantenimiento web",
     "estado": "COTEJADO",
     "remesa_directa_id": None,
     "servicio_id": 1,
     "lineas_analitica": [{"id_analitica": 1, "porcentaje": 100.0}],
     "lineas_iva": [{"porcentaje_iva": 21.0, "base": 850.00, "cuota": 178.50}]},
    {"id_gasto": 2, "codigo": "GD-2026-002",
     "tipo": "TARJETA",
     "proveedor_id": 2,
     "tarjeta_id": 1, "empleado_id": 1,
     "fecha_documento": "2026-03-15",
     "fecha_cargo_real": "2026-03-16",
     "importe_base": 320.00, "importe_iva": 67.20, "importe_total": 387.20,
     "irpf": 0.0,
     "referencia_factura": "TK-0045",
     "concepto": "Material oficina",
     "estado": "BORRADOR",
     "remesa_directa_id": None,
     "servicio_id": 1,
     "lineas_analitica": [],
     "lineas_iva": [{"porcentaje_iva": 21.0, "base": 320.00, "cuota": 67.20}]},
]

REMESAS_DIRECTAS: list[dict] = [
    {"id_remesa_directa": 1, "numero": 1,
     "tipo": "DOMICILIACIONES",
     "periodo": "2026-03",
     "estado": "ABIERTA",
     "cuenta_bancaria_id": 1,
     "servicio_id": 1,
     "fecha_creacion": "2026-03-31",
     "fecha_cierre": None},
]


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
