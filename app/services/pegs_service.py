from app.schemas.pegs import PegCrear, PegCambioEstado
from app.services.proveedores_service import proveedores_db as _proveedores
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# DATOS SIMULADOS EN MEMORIA (sustituir por BD real cuando esté disponible)
# ──────────────────────────────────────────────────────────────────────────────

_servicios = [
    {"id_servicio": 1, "codigo": "HV",  "nombre": "Hospital Veterinario"},
    {"id_servicio": 2, "codigo": "CI",  "nombre": "Centro de Idiomas"},
    {"id_servicio": 3, "codigo": "DP",  "nombre": "Desarrollo Profesional"},
]

_proyectos = [
    {"id_proyecto": 1, "id_servicio": 1, "codigo": "HV-GEN", "nombre": "Hospital Veterinario General"},
    {"id_proyecto": 2, "id_servicio": 2, "codigo": "ESP",    "nombre": "Español"},
    {"id_proyecto": 3, "id_servicio": 2, "codigo": "IMO",    "nombre": "Idiomas Modernos"},
    {"id_proyecto": 4, "id_servicio": 3, "codigo": "INC",    "nombre": "Incofi"},
    {"id_proyecto": 5, "id_servicio": 3, "codigo": "EXP",    "nombre": "Experience Plus"},
]

SERVICIOS_PROYECTOS_TODOS = [
    {"id": 1, "nombre": "Hospital Veterinario", "proyectos": [
        {"id": 1, "nombre": "Hospital Veterinario General"},
    ]},
    {"id": 2, "nombre": "Centro de Idiomas", "proyectos": [
        {"id": 2, "nombre": "Español"},
        {"id": 3, "nombre": "Idiomas Modernos"},
    ]},
    {"id": 3, "nombre": "Desarrollo Profesional", "proyectos": [
        {"id": 4, "nombre": "Incofi"},
        {"id": 5, "nombre": "Experience Plus"},
    ]},
]

_analiticas = [
    {"id_analitica": 1, "id_servicio": 1, "id_proyecto": 1, "nivel_1": "6", "nivel_2": "2", "descripcion": "Hospital Veterinario General",          "activo": True},
    {"id_analitica": 2, "id_servicio": 2, "id_proyecto": 2, "nivel_1": "2", "nivel_2": "1", "descripcion": "Centro de Idiomas - Español",            "activo": True},
    {"id_analitica": 3, "id_servicio": 2, "id_proyecto": 3, "nivel_1": "2", "nivel_2": "1", "descripcion": "Centro de Idiomas - Idiomas Modernos",   "activo": True},
    {"id_analitica": 4, "id_servicio": 3, "id_proyecto": 4, "nivel_1": "3", "nivel_2": "4", "descripcion": "Desarrollo Profesional - INCOFI",        "activo": True},
    {"id_analitica": 5, "id_servicio": 3, "id_proyecto": 5, "nivel_1": "3", "nivel_2": "8", "descripcion": "Desarrollo Profesional - Experience Plus", "activo": True},
]

_formas_pago = [
    {"id_forma_pago": 1, "codigo": "TRANSFERENCIA", "nombre": "Transferencia"},
    {"id_forma_pago": 2, "codigo": "DOMICILIACION", "nombre": "Domiciliación"},
    {"id_forma_pago": 3, "codigo": "CAJA",          "nombre": "Caja"},
    {"id_forma_pago": 4, "codigo": "TARJETA",       "nombre": "Tarjeta"},
]

_tipos_peg = [
    {"id_peg_tipo": 1, "codigo": "FACTURA",      "nombre": "Factura"},
    {"id_peg_tipo": 2, "codigo": "PRESUPUESTO",  "nombre": "Presupuesto"},
]

_estados = [
    {"id_peg_estado": 1, "codigo": "PENDIENTE",  "nombre": "Pendiente",  "orden_estado": 1},
    {"id_peg_estado": 2, "codigo": "VALIDADO",   "nombre": "Validado",   "orden_estado": 2},
    {"id_peg_estado": 3, "codigo": "EN_REMESA",  "nombre": "En remesa",  "orden_estado": 3},
    {"id_peg_estado": 4, "codigo": "PAGADO",     "nombre": "Pagado",     "orden_estado": 4},
    {"id_peg_estado": 5, "codigo": "INCIDENCIA", "nombre": "Incidencia", "orden_estado": 5},
]

# _proveedores se importa desde proveedores_service para que ambos módulos
# compartan el mismo objeto en memoria y los cambios sean visibles en ambos lados.

_pegs = [
    {
        "id_peg": 1, "codigo_peg": "PEG-2026-0001",
        "id_servicio": 1, "id_proyecto": 1, "id_proveedor": 3, "id_peg_tipo": 1,
        "numero_documento": "FAC-001", "fecha_documento": "2026-01-15",
        "fecha_recepcion": "2026-01-16", "fecha_vencimiento": "2026-02-15",
        "descripcion_gasto": "Compra de material veterinario",
        "observaciones": "Urgente para quirófano",
        "id_forma_pago_prevista": 1,
        "lineas": [{"tipo_iva": 21, "base_imponible": 1000.00}],
        "base_imponible": 1000.00, "importe_iva": 210.00, "importe_irpf": 0.00, "importe_total": 1210.00,
        "id_peg_estado": 4, "lineas_analitica": [{"servicio_id": 1, "proyecto_id": 1, "porcentaje": 100.0}], "id_remesa": None, "creado_por": 1,
        "fecha_creacion": "2026-01-16", "fecha_actualizacion": "2026-01-22", "fecha_pago": "2026-01-22",
        "numero_factura_interno": "F6001ENE", "id_cuenta_gasto": 3, "cuenta_gasto": "623000", "cuenta_cliente_proveedor": "4100003", "factura_recibida": True,
    },
    {
        "id_peg": 2, "codigo_peg": "PEG-2026-0002",
        "id_servicio": 2, "id_proyecto": 2, "id_proveedor": 4, "id_peg_tipo": 2,
        "numero_documento": "PRE-101", "fecha_documento": "2026-02-10",
        "fecha_recepcion": "2026-02-10", "fecha_vencimiento": None,
        "descripcion_gasto": "Presupuesto traducción material promocional",
        "observaciones": None,
        "id_forma_pago_prevista": 1,
        "lineas": [{"tipo_iva": 21, "base_imponible": 500.00}],
        "base_imponible": 500.00, "importe_iva": 105.00, "importe_irpf": 0.00, "importe_total": 605.00,
        "id_peg_estado": 3, "lineas_analitica": [{"servicio_id": 2, "proyecto_id": 2, "porcentaje": 100.0}], "id_remesa": 2, "creado_por": 2,
        "fecha_creacion": "2026-02-10", "fecha_actualizacion": "2026-02-10", "fecha_pago": None,
        "numero_factura_interno": None, "id_cuenta_gasto": None, "cuenta_gasto": "", "cuenta_cliente_proveedor": "", "factura_recibida": False,
    },
    {
        "id_peg": 3, "codigo_peg": "PEG-2026-0003",
        "id_servicio": 2, "id_proyecto": 3, "id_proveedor": 2, "id_peg_tipo": 1,
        "numero_documento": "FAC-889", "fecha_documento": "2026-02-20",
        "fecha_recepcion": "2026-02-21", "fecha_vencimiento": "2026-03-21",
        "descripcion_gasto": "Servicio externo de traducción jurada",
        "observaciones": "Pendiente de validación administrativa",
        "id_forma_pago_prevista": 1,
        "lineas": [{"tipo_iva": 21, "base_imponible": 320.00}],
        "base_imponible": 320.00, "importe_iva": 67.20, "importe_irpf": 0.00, "importe_total": 387.20,
        "id_peg_estado": 3, "lineas_analitica": [{"servicio_id": 2, "proyecto_id": 3, "porcentaje": 100.0}], "id_remesa": 2, "creado_por": 2,
        "fecha_creacion": "2026-02-21", "fecha_actualizacion": "2026-02-22", "fecha_pago": None,
        "numero_factura_interno": None, "id_cuenta_gasto": None, "cuenta_gasto": "", "cuenta_cliente_proveedor": "", "factura_recibida": False,
    },
    {
        "id_peg": 4, "codigo_peg": "PEG-2026-0004",
        "id_servicio": 3, "id_proyecto": 4, "id_proveedor": 1, "id_peg_tipo": 1,
        "numero_documento": "FAC-555", "fecha_documento": "2026-03-01",
        "fecha_recepcion": "2026-03-02", "fecha_vencimiento": "2026-04-01",
        "descripcion_gasto": "Material para jornadas de empleabilidad",
        "observaciones": "Existe incidencia por falta de autorización",
        "id_forma_pago_prevista": 1,
        "lineas": [
            {"tipo_iva": 21, "base_imponible": 500.00},
            {"tipo_iva": 10, "base_imponible": 200.00},
        ],
        "base_imponible": 700.00, "importe_iva": 125.00, "importe_irpf": 0.00, "importe_total": 825.00,
        "id_peg_estado": 5, "lineas_analitica": [], "id_remesa": None, "creado_por": 3,
        "fecha_creacion": "2026-03-02", "fecha_actualizacion": "2026-03-03", "fecha_pago": None,
        "numero_factura_interno": None, "id_cuenta_gasto": None, "cuenta_gasto": "", "cuenta_cliente_proveedor": "", "factura_recibida": False,
    },
    {
        "id_peg": 5, "codigo_peg": "PEG-2026-0005",
        "id_servicio": 1, "id_proyecto": 1, "id_proveedor": 3, "id_peg_tipo": 1,
        "numero_documento": "FAC-002", "fecha_documento": "2026-03-10",
        "fecha_recepcion": "2026-03-11", "fecha_vencimiento": "2026-04-10",
        "descripcion_gasto": "Reactivos de laboratorio veterinario",
        "observaciones": None,
        "id_forma_pago_prevista": 1,
        "lineas": [{"tipo_iva": 21, "base_imponible": 750.00}],
        "base_imponible": 750.00, "importe_iva": 157.50, "importe_irpf": 0.00, "importe_total": 907.50,
        "id_peg_estado": 2, "lineas_analitica": [{"servicio_id": 1, "proyecto_id": 1, "porcentaje": 100.0}], "id_remesa": None, "creado_por": 1,
        "fecha_creacion": "2026-03-11", "fecha_actualizacion": "2026-03-12", "fecha_pago": None,
        "numero_factura_interno": None, "id_cuenta_gasto": None, "cuenta_gasto": "", "cuenta_cliente_proveedor": "", "factura_recibida": False,
    },
]

_historial = [
    {"id_peg": 1, "fecha_cambio": "2026-01-16", "estado_origen": None,        "estado_destino": "Pendiente",  "comentario": "PEG creada",                          "realizado_por": "Gestor H. Veterinario"},
    {"id_peg": 1, "fecha_cambio": "2026-01-17", "estado_origen": "Pendiente", "estado_destino": "Validado",   "comentario": "PEG validada por gestor económico",   "realizado_por": "José Carlos Alonso"},
    {"id_peg": 1, "fecha_cambio": "2026-01-20", "estado_origen": "Validado",  "estado_destino": "Pagado",     "comentario": "PEG pagada",                          "realizado_por": "José Carlos Alonso"},
    {"id_peg": 2, "fecha_cambio": "2026-02-10", "estado_origen": None,        "estado_destino": "Pendiente",  "comentario": "PEG creada",                          "realizado_por": "Gestor C. Idiomas"},
    {"id_peg": 3, "fecha_cambio": "2026-02-21", "estado_origen": None,        "estado_destino": "Pendiente",  "comentario": "PEG creada",                          "realizado_por": "Gestor C. Idiomas"},
    {"id_peg": 4, "fecha_cambio": "2026-03-02", "estado_origen": None,        "estado_destino": "Pendiente",  "comentario": "PEG creada",                          "realizado_por": "Gestor Económico FGULEM"},
    {"id_peg": 4, "fecha_cambio": "2026-03-03", "estado_origen": "Pendiente", "estado_destino": "Incidencia", "comentario": "Falta autorización firmada",           "realizado_por": "José Carlos Alonso"},
    {"id_peg": 5, "fecha_cambio": "2026-03-11", "estado_origen": None,        "estado_destino": "Pendiente",  "comentario": "PEG creada",                          "realizado_por": "Gestor H. Veterinario"},
    {"id_peg": 5, "fecha_cambio": "2026-03-12", "estado_origen": "Pendiente", "estado_destino": "Validado",   "comentario": "PEG validada",                        "realizado_por": "José Carlos Alonso"},
]

_incidencias = [
    {"id_peg": 4, "descripcion": "Falta autorización firmada del responsable", "abierta": True, "fecha_creacion": "2026-03-03", "creada_por": "José Carlos Alonso"},
]


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _estado_por_id(id_estado):
    return next((e for e in _estados if e["id_peg_estado"] == id_estado), {})

def _proveedor_por_id(id_proveedor):
    return next((p for p in _proveedores if p["id_proveedor"] == id_proveedor), {})

def _servicio_por_id(id_servicio):
    return next((s for s in _servicios if s["id_servicio"] == id_servicio), {})

def _proyecto_por_id(id_proyecto):
    return next((p for p in _proyectos if p["id_proyecto"] == id_proyecto), None)

def _tipo_por_id(id_tipo):
    return next((t for t in _tipos_peg if t["id_peg_tipo"] == id_tipo), {})

def _forma_pago_por_id(id_fp):
    return next((f for f in _formas_pago if f["id_forma_pago"] == id_fp), {})


def get_analitica_por_servicio_proyecto(
    id_servicio: int, id_proyecto: int | None
) -> dict | None:
    return next(
        (a for a in _analiticas
         if a["id_servicio"] == id_servicio
         and a.get("id_proyecto") == id_proyecto
         and a.get("activo", True)),
        None,
    )


# ──────────────────────────────────────────────────────────────────────────────
# DATOS FORMULARIO
# ──────────────────────────────────────────────────────────────────────────────

def obtener_datos_formulario() -> dict:
    return {
        "servicios":   _servicios,
        "proveedores": _proveedores,
        "tipos":       _tipos_peg,
        "formas_pago": _formas_pago,
        "proyectos":   _proyectos,
        "analiticas":  _analiticas,
    }

def obtener_proveedor_json(id_proveedor: int) -> dict | None:
    return _proveedor_por_id(id_proveedor) or None

def get_proveedores() -> list[dict]:
    return list(_proveedores)


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

def listar_pegs(id_servicio=None, id_estado=None, texto=None) -> list[dict]:
    resultado = []
    for p in _pegs:
        if id_servicio and p["id_servicio"] != id_servicio:
            continue
        if id_estado and p["id_peg_estado"] != id_estado:
            continue
        proveedor = _proveedor_por_id(p["id_proveedor"])
        servicio  = _servicio_por_id(p["id_servicio"])
        estado    = _estado_por_id(p["id_peg_estado"])
        if texto:
            t = texto.lower()
            if t not in p["codigo_peg"].lower() and \
               t not in p["descripcion_gasto"].lower() and \
               t not in proveedor.get("razon_social", "").lower():
                continue
        resultado.append({
            **p,
            "nombre_proveedor": proveedor.get("razon_social", ""),
            "nombre_servicio":  servicio.get("nombre", ""),
            "nombre_estado":    estado.get("nombre", ""),
            "codigo_estado":    estado.get("codigo", ""),
        })
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────────────────────────────────────

def obtener_peg(id_peg: int) -> dict | None:
    try:
        print(f"[DEBUG] obtener_peg({id_peg}) — buscando en _pegs")
        peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
        print(f"[DEBUG] peg raw: {peg}")
        if not peg:
            return None

        print(f"[DEBUG] buscando proveedor id={peg.get('id_proveedor')}")
        proveedor = _proveedor_por_id(peg.get("id_proveedor")) or {}
        print(f"[DEBUG] proveedor: {proveedor}")

        print(f"[DEBUG] buscando servicio id={peg.get('id_servicio')}")
        servicio  = _servicio_por_id(peg.get("id_servicio"))   or {}
        print(f"[DEBUG] servicio: {servicio}")

        print(f"[DEBUG] buscando estado id={peg.get('id_peg_estado')}")
        estado    = _estado_por_id(peg.get("id_peg_estado"))   or {}
        print(f"[DEBUG] estado: {estado}")

        print(f"[DEBUG] buscando tipo id={peg.get('id_peg_tipo')}")
        tipo      = _tipo_por_id(peg.get("id_peg_tipo"))       or {}
        print(f"[DEBUG] tipo: {tipo}")

        print(f"[DEBUG] buscando forma_pago id={peg.get('id_forma_pago_prevista')}")
        forma     = _forma_pago_por_id(peg.get("id_forma_pago_prevista")) or {}
        print(f"[DEBUG] forma_pago: {forma}")

        print(f"[DEBUG] buscando proyecto id={peg.get('id_proyecto')}")
        proyecto  = _proyecto_por_id(peg.get("id_proyecto"))
        print(f"[DEBUG] proyecto: {proyecto}")

        id_remesa = peg.get("id_remesa")
        print(f"[DEBUG] id_remesa: {id_remesa}")
        codigo_remesa = None
        if id_remesa is not None:
            from app.services import remesas_service
            print(f"[DEBUG] buscando remesa id={id_remesa}")
            remesa = remesas_service.obtener_remesa(id_remesa)
            print(f"[DEBUG] remesa: {remesa}")
            if remesa:
                codigo_remesa = remesa.get("codigo_remesa")

        print(f"[DEBUG] construyendo dict de retorno")
        resultado = {
            **peg,
            "nombre_proveedor":  proveedor.get("razon_social", ""),
            "cif_nif":           proveedor.get("cif_nif", ""),
            "iban":              proveedor.get("iban"),
            "nombre_servicio":   servicio.get("nombre", ""),
            "nombre_estado":     estado.get("nombre", "Desconocido"),
            "codigo_estado":     estado.get("codigo", "PENDIENTE"),
            "nombre_tipo":       tipo.get("nombre", ""),
            "nombre_forma_pago": forma.get("nombre", ""),
            "nombre_proyecto":   proyecto.get("nombre") if proyecto else "—",
            "id_remesa":         id_remesa,
            "codigo_remesa":     codigo_remesa,
            "documentos":        peg.get("documentos", []),
            "historial":         [h for h in _historial   if h["id_peg"] == id_peg],
            "incidencias":       [i for i in _incidencias if i["id_peg"] == id_peg],
        }
        print(f"[DEBUG] obtener_peg({id_peg}) OK")
        return resultado
    except Exception as e:
        import traceback
        print(f"[ERROR] obtener_peg({id_peg}) falló: {e}")
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────────────────────────────────────
# CÁLCULO DE TOTALES
# ──────────────────────────────────────────────────────────────────────────────

def calcular_totales(lineas: list[dict], tiene_irpf: bool = False, tipo_irpf: float = 0.0) -> dict:
    base = sum(l["base_imponible"] for l in lineas)
    iva  = sum(round(l["base_imponible"] * l["tipo_iva"] / 100, 2) for l in lineas)
    irpf = round(base * tipo_irpf / 100, 2) if tiene_irpf else 0.0
    return {
        "base_imponible_total": round(base, 2),
        "importe_iva_total":    round(iva, 2),
        "importe_irpf":         irpf,
        "importe_total":        round(base + iva - irpf, 2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CREACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def crear_peg(data: PegCrear) -> dict:
    anio = datetime.now().year
    siguiente = sum(1 for p in _pegs if str(p["fecha_creacion"]).startswith(str(anio))) + 1
    codigo_peg = f"PEG-{anio}-{siguiente:04d}"
    id_peg = max((p["id_peg"] for p in _pegs), default=0) + 1

    lineas = [l.model_dump() for l in data.lineas]
    totales = calcular_totales(lineas, data.tiene_irpf, data.tipo_irpf)

    nuevo = {
        "id_peg":              id_peg,
        "codigo_peg":          codigo_peg,
        "id_peg_estado":       1,
        "id_remesa":           None,
        "fecha_creacion":      datetime.now().strftime("%Y-%m-%d"),
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d"),
        "fecha_pago":          None,
        **data.model_dump(exclude={"lineas"}),
        "lineas":              lineas,
        "base_imponible":      totales["base_imponible_total"],
        "importe_iva":         totales["importe_iva_total"],
        "importe_irpf":        totales["importe_irpf"],
        "importe_total":       totales["importe_total"],
        "lineas_analitica":    [],
        "cuenta_gasto":        "",
    }
    _pegs.append(nuevo)
    _historial.append({
        "id_peg":          id_peg,
        "fecha_cambio":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen":   None,
        "estado_destino":  "Pendiente",
        "comentario":      "PEG creada",
        "realizado_por":   "Usuario",
    })
    return {"id_peg": id_peg, "codigo_peg": codigo_peg}


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO
# ──────────────────────────────────────────────────────────────────────────────

def cambiar_estado_peg(id_peg: int, cambio: PegCambioEstado) -> bool:
    peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
    if not peg:
        return False
    estado_origen = _estado_por_id(peg["id_peg_estado"]).get("nombre")
    peg["id_peg_estado"] = cambio.id_peg_estado_destino
    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")
    _historial.append({
        "id_peg": id_peg,
        "fecha_cambio": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen": estado_origen,
        "estado_destino": _estado_por_id(cambio.id_peg_estado_destino).get("nombre", ""),
        "comentario": cambio.comentario,
        "realizado_por": "Usuario",
    })
    return True


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO DIRECTO (sin schema PegCambioEstado)
# ──────────────────────────────────────────────────────────────────────────────

def cambiar_estado_directo(id_peg: int, nuevo_estado_id: int, nombre_usuario: str, comentario: str = None) -> bool:
    peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
    if not peg:
        return False
    estado_origen = _estado_por_id(peg["id_peg_estado"]).get("nombre")
    peg["id_peg_estado"] = nuevo_estado_id
    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")
    _historial.append({
        "id_peg": id_peg,
        "fecha_cambio": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen": estado_origen,
        "estado_destino": _estado_por_id(nuevo_estado_id).get("nombre", ""),
        "comentario": comentario,
        "realizado_por": nombre_usuario,
    })
    return True


# ──────────────────────────────────────────────────────────────────────────────
# FILTROS
# ──────────────────────────────────────────────────────────────────────────────

def obtener_estados() -> list[dict]:
    return _estados

def obtener_servicios() -> list[dict]:
    return _servicios


# ──────────────────────────────────────────────────────────────────────────────
# ACCESO A DATOS RAW (para mutación directa)
# ──────────────────────────────────────────────────────────────────────────────

def get_peg_raw(id_peg: int) -> dict | None:
    """Devuelve el dict mutable del mock (sin enriquecer)."""
    return next((p for p in _pegs if p["id_peg"] == id_peg), None)


# Alias público para uso en servicios auxiliares
get_peg_por_id = get_peg_raw


def listar_pegs_todos() -> list[dict]:
    """Devuelve todos los PEGs en bruto (sin enriquecer). Usado por factura_interna_service."""
    return list(_pegs)


def contar_pagados_sin_factura() -> int:
    return sum(
        1 for p in _pegs
        if p["id_peg_estado"] == 4 and not p.get("factura_recibida", False)
    )


def obtener_kpis_dashboard(usuario: dict, id_servicio_filtro: int | None = None) -> dict:
    """Calcula los KPIs del dashboard adaptados al rol del usuario.

    id_servicio_filtro: permite a GESTOR_ECONOMICO/ADMIN filtrar por servicio.
    """
    from collections import defaultdict

    es_servicio = usuario.get("rol") == "GESTOR_SERVICIO"

    # El GESTOR_SERVICIO siempre ve solo su servicio.
    # GESTOR_ECONOMICO/ADMIN pueden filtrar opcionalmente.
    if es_servicio:
        id_servicio_efectivo = usuario.get("id_servicio")
    else:
        id_servicio_efectivo = id_servicio_filtro  # None = todos

    pegs = listar_pegs(id_servicio=id_servicio_efectivo)

    # ── Conteos e importes por estado ───────────────────────────
    conteos  = defaultdict(int)
    importes = defaultdict(float)
    for p in pegs:
        cod = p["codigo_estado"]
        conteos[cod]  += 1
        importes[cod] += p.get("importe_total", 0)

    kpis = {
        "pendiente":          conteos["PENDIENTE"],
        "incidencia":         conteos["INCIDENCIA"],
        "validado":           conteos["VALIDADO"],
        "en_remesa":          conteos["EN_REMESA"],
        "pagado":             conteos["PAGADO"],
        "importe_pendiente":  importes["PENDIENTE"],
        "importe_incidencia": importes["INCIDENCIA"],
        "importe_validado":   importes["VALIDADO"],
        "importe_en_remesa":  importes["EN_REMESA"],
        "importe_pagado":     importes["PAGADO"],
        "total_pegs":         len(pegs),
        "servicio_filtro":    id_servicio_efectivo,
    }

    # ── Solo para roles con visibilidad global ──────────────────
    if not es_servicio:
        # Desglose de PENDIENTES por servicio (sobre el universo sin filtro)
        todos = listar_pegs() if id_servicio_efectivo else pegs
        por_servicio = {}  # {id_servicio: {"nombre": str, "count": int}}
        for p in todos:
            if p["codigo_estado"] == "PENDIENTE":
                sid = p["id_servicio"]
                if sid not in por_servicio:
                    por_servicio[sid] = {"id": sid, "nombre": p["nombre_servicio"], "count": 0}
                por_servicio[sid]["count"] += 1
        kpis["pendiente_por_servicio"] = list(por_servicio.values())

        # PEGs validadas sin remesa
        kpis["validado_sin_remesa"] = sum(
            1 for p in pegs
            if p["codigo_estado"] == "VALIDADO" and not p.get("id_remesa")
        )

        # Pagados sin factura
        kpis["pagados_sin_factura"] = contar_pagados_sin_factura()

        # Remesas abiertas (RT)
        from app.services import remesas_service
        kpis["remesas_abiertas"] = len(remesas_service.listar_remesas(estado="ABIERTA"))

        # Movimientos bancarios pendientes de cotejar
        from app.services import mock_movimientos as _mov_svc
        kpis["mov_pendientes"] = sum(
            1 for m in _mov_svc.listar_movimientos(estado="PENDIENTE")
            if m.get("importe", 0) < 0
        )

        # Remesas directas abiertas
        from app.services.remesas_directas_service import listar_remesas as _listar_rd
        kpis["rd_abiertas"] = sum(
            1 for r in _listar_rd() if r.get("estado") == "ABIERTA"
        )

    # Solicitudes KPIs (todos los roles)
    from app.services.solicitudes_service import listar_solicitudes
    if es_servicio:
        todas_sol = listar_solicitudes(id_servicio=usuario.get("id_servicio"))
    else:
        todas_sol = listar_solicitudes()
    kpis["sol_pendientes"] = sum(
        1 for s in todas_sol if s["estado_solicitud"] == "PENDIENTE_AUTORIZACION"
    )
    kpis["sol_autorizadas_sin_peg"] = sum(
        1 for s in todas_sol
        if s["estado_solicitud"] == "AUTORIZADA" and not s.get("id_peg_generado")
    )

    return kpis


# ──────────────────────────────────────────────────────────────────────────────
# EDICIÓN DE PEG
# ──────────────────────────────────────────────────────────────────────────────

def editar_peg(
    id_peg: int,
    campos: dict,
    nuevo_estado_id: int | None,
    nombre_usuario: str,
    motivo: str | None,
) -> dict:
    """Actualiza campos editables y opcionalmente cambia el estado del PEG."""
    peg = get_peg_raw(id_peg)
    if not peg:
        return {"ok": False, "error": "PEG no encontrada"}

    for campo in [
        "descripcion_gasto", "numero_documento", "fecha_documento",
        "fecha_vencimiento", "observaciones", "id_forma_pago_prevista",
        "id_proveedor",
    ]:
        if campo in campos:
            peg[campo] = campos[campo]

    if "lineas" in campos and campos["lineas"]:
        peg["lineas"] = campos["lineas"]
        totales = calcular_totales(campos["lineas"])
        peg["base_imponible"] = totales["base_imponible_total"]
        peg["importe_iva"]    = totales["importe_iva_total"]
        peg["importe_irpf"]   = totales["importe_irpf"]
        peg["importe_total"]  = totales["importe_total"]

    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")

    if nuevo_estado_id is not None:
        # EN_REMESA → VALIDADO: quitar la remesa asignada
        if peg["id_peg_estado"] == 3 and nuevo_estado_id == 2:
            peg["id_remesa"] = None
        cambiar_estado_directo(id_peg, nuevo_estado_id, nombre_usuario, motivo or "")

    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# PEGS VALIDADOS SIN REMESA
# ──────────────────────────────────────────────────────────────────────────────

def get_pegs_validados_sin_remesa() -> list[dict]:
    """PEGs con estado VALIDADO, sin remesa asignada y con analítica."""
    resultado = []
    for p in _pegs:
        if p["id_peg_estado"] != 2:           # solo VALIDADO
            continue
        if p.get("id_remesa") is not None:    # ya en una remesa
            continue
        if not p.get("lineas_analitica"):      # sin analítica
            continue
        proveedor = _proveedor_por_id(p["id_proveedor"])
        servicio  = _servicio_por_id(p["id_servicio"])
        resultado.append({
            "id_peg":           p["id_peg"],
            "codigo_peg":       p["codigo_peg"],
            "proveedor_nombre": proveedor.get("razon_social", ""),
            "descripcion_gasto": p["descripcion_gasto"],
            "importe_total":    p["importe_total"],
            "servicio_nombre":  servicio.get("nombre", ""),
        })
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
# ASIGNACIÓN / BAJA DE REMESA
# ──────────────────────────────────────────────────────────────────────────────

def asignar_a_remesa(id_peg: int, id_remesa: int, nombre_usuario: str) -> bool:
    peg = get_peg_raw(id_peg)
    if not peg:
        return False
    estado_origen = _estado_por_id(peg["id_peg_estado"]).get("nombre")
    peg["id_remesa"]           = id_remesa
    peg["id_peg_estado"]       = 3          # EN_REMESA
    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")
    _historial.append({
        "id_peg":          id_peg,
        "fecha_cambio":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen":   estado_origen,
        "estado_destino":  "En remesa",
        "comentario":      f"Añadido a remesa",
        "realizado_por":   nombre_usuario,
    })
    return True


def quitar_de_remesa(id_peg: int, nombre_usuario: str) -> bool:
    peg = get_peg_raw(id_peg)
    if not peg:
        return False
    estado_origen = _estado_por_id(peg["id_peg_estado"]).get("nombre")
    peg["id_remesa"]           = None
    peg["id_peg_estado"]       = 2          # VALIDADO
    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")
    _historial.append({
        "id_peg":          id_peg,
        "fecha_cambio":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen":   estado_origen,
        "estado_destino":  "Validado",
        "comentario":      "Retirado de remesa",
        "realizado_por":   nombre_usuario,
    })
    return True


# ──────────────────────────────────────────────────────────────────────────────
# ELIMINAR PEG
# ──────────────────────────────────────────────────────────────────────────────

def eliminar_peg(id_peg: int, usuario: dict) -> dict:
    global _pegs
    peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
    if not peg:
        return {"ok": False, "error": "PEG no encontrado"}
    estados_permitidos = ["PENDIENTE", "VALIDADO", "INCIDENCIA"]
    estado = _estado_por_id(peg["id_peg_estado"])
    codigo_estado = estado.get("codigo", "")
    if codigo_estado not in estados_permitidos:
        return {"ok": False, "error": f"No se puede eliminar un PEG en estado {codigo_estado}"}
    _pegs = [p for p in _pegs if p["id_peg"] != id_peg]
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# ANALÍTICAS POR SERVICIO
# ──────────────────────────────────────────────────────────────────────────────

def obtener_analiticas_servicio(id_servicio: int) -> list:
    return [a for a in _analiticas if a["id_servicio"] == id_servicio]


def get_servicios_proyectos_todos() -> list:
    result = []
    for s in SERVICIOS_PROYECTOS_TODOS:
        analitica_servicio = next(
            (a for a in _analiticas if a["id_servicio"] == s["id"]), {}
        )
        proyectos = []
        for p in s["proyectos"]:
            analitica = next(
                (a for a in _analiticas if a["id_servicio"] == s["id"] and a["id_proyecto"] == p["id"]),
                {}
            )
            proyectos.append({
                **p,
                "nivel_1": analitica_servicio.get("nivel_1", ""),
                "nivel_2": analitica.get("nivel_2", ""),
            })
        result.append({**s, "proyectos": proyectos})
    return result


# ──────────────────────────────────────────────────────────────────────────────
# VALIDAR PEG (con analítica)
# ──────────────────────────────────────────────────────────────────────────────

def validar_peg(
    id_peg: int,
    cuenta_gasto: str,
    lineas_analitica: list,
    usuario: dict,
) -> dict:
    """Valida un PEG asignando cuenta_gasto (str) y líneas analíticas {servicio_id, proyecto_id, porcentaje}."""
    peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
    if not peg:
        return {"ok": False, "error": "PEG no encontrado"}
    estado = _estado_por_id(peg["id_peg_estado"])
    if estado.get("codigo") != "PENDIENTE":
        return {"ok": False, "error": "Solo se pueden validar PEGs en estado PENDIENTE"}
    if not cuenta_gasto.strip():
        return {"ok": False, "error": "La cuenta de gasto es obligatoria"}
    if not lineas_analitica:
        return {"ok": False, "error": "Debe añadir al menos una línea analítica"}
    if len(lineas_analitica) > 3:
        return {"ok": False, "error": "Máximo 3 líneas analíticas permitidas"}
    if any(l.get("porcentaje", 0) <= 0 for l in lineas_analitica):
        return {"ok": False, "error": "Todos los porcentajes deben ser positivos"}
    suma = sum(l.get("porcentaje", 0) for l in lineas_analitica)
    if abs(suma - 100.0) > 0.01:
        return {"ok": False, "error": f"La suma de porcentajes debe ser 100 (actual: {suma:.2f})"}

    estado_origen = estado.get("nombre")
    peg["id_peg_estado"]       = 2  # VALIDADO
    peg["lineas_analitica"]    = lineas_analitica
    peg["cuenta_gasto"]        = cuenta_gasto.strip()
    peg["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d")

    _historial.append({
        "id_peg":          id_peg,
        "fecha_cambio":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "estado_origen":   estado_origen,
        "estado_destino":  "Validado",
        "comentario":      "Validado por gestor económico",
        "realizado_por":   usuario.get("nombre_completo", usuario.get("login", "")),
    })
    return {"ok": True}


def obtener_lineas_analitica_peg(id_peg: int) -> list:
    peg = next((p for p in _pegs if p["id_peg"] == id_peg), None)
    if not peg:
        return []
    result = []
    for l in peg.get("lineas_analitica", []):
        servicio = _servicio_por_id(l.get("servicio_id", 0))
        proyecto = _proyecto_por_id(l.get("proyecto_id"))
        result.append({
            **l,
            "nombre_servicio": servicio.get("nombre", ""),
            "nombre_proyecto": proyecto.get("nombre", "") if proyecto else "",
        })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# CUENTAS DE GASTO
# ──────────────────────────────────────────────────────────────────────────────

CUENTAS_GASTO = [
    {"id_cuenta_gasto": 1, "codigo": "621000", "descripcion": "Reparaciones y conservación", "activo": True},
    {"id_cuenta_gasto": 2, "codigo": "622000", "descripcion": "Material de oficina", "activo": True},
    {"id_cuenta_gasto": 3, "codigo": "623000", "descripcion": "Servicios profesionales", "activo": True},
    {"id_cuenta_gasto": 4, "codigo": "624000", "descripcion": "Transportes", "activo": True},
    {"id_cuenta_gasto": 5, "codigo": "625000", "descripcion": "Primas de seguros", "activo": True},
    {"id_cuenta_gasto": 6, "codigo": "626000", "descripcion": "Servicios bancarios", "activo": True},
    {"id_cuenta_gasto": 7, "codigo": "627000", "descripcion": "Publicidad y propaganda", "activo": True},
    {"id_cuenta_gasto": 8, "codigo": "628000", "descripcion": "Suministros", "activo": True},
    {"id_cuenta_gasto": 9, "codigo": "629000", "descripcion": "Otros servicios", "activo": True},
]


def listar_cuentas_gasto() -> list[dict]:
    return [c for c in CUENTAS_GASTO if c["activo"]]


def listar_todas_cuentas_gasto() -> list[dict]:
    return list(CUENTAS_GASTO)


def get_cuenta_gasto_por_id(id_cuenta_gasto: int) -> dict | None:
    return next((c for c in CUENTAS_GASTO if c["id_cuenta_gasto"] == id_cuenta_gasto), None)


def crear_cuenta_gasto(codigo: str, descripcion: str) -> dict:
    nuevo_id = max((c["id_cuenta_gasto"] for c in CUENTAS_GASTO), default=0) + 1
    nueva = {"id_cuenta_gasto": nuevo_id, "codigo": codigo.strip(), "descripcion": descripcion.strip(), "activo": True}
    CUENTAS_GASTO.append(nueva)
    return nueva


def actualizar_cuenta_gasto(id_cuenta_gasto: int, codigo: str, descripcion: str, activo: bool) -> bool:
    cuenta = get_cuenta_gasto_por_id(id_cuenta_gasto)
    if not cuenta:
        return False
    cuenta["codigo"] = codigo.strip()
    cuenta["descripcion"] = descripcion.strip()
    cuenta["activo"] = activo
    return True


def toggle_cuenta_gasto(id_cuenta_gasto: int) -> bool:
    cuenta = get_cuenta_gasto_por_id(id_cuenta_gasto)
    if not cuenta:
        return False
    cuenta["activo"] = not cuenta["activo"]
    return True


# ──────────────────────────────────────────────────────────────────────────────
# PARÁMETROS DEL SISTEMA
# ──────────────────────────────────────────────────────────────────────────────

PARAMETROS_SISTEMA = {
    "cuenta_saco": "440000",   # Cuenta genérica para proveedores sin cuenta propia
    "codigo_empresa_a3con": "00001",
}


def get_parametro(clave: str):
    return PARAMETROS_SISTEMA.get(clave)


# ──────────────────────────────────────────────────────────────────────────────
# GESTIÓN DE DOCUMENTOS ADJUNTOS
# ──────────────────────────────────────────────────────────────────────────────

def _siguiente_id_documento() -> int:
    todos = [doc for p in _pegs for doc in p.get("documentos", [])]
    if not todos:
        return 1
    return max(d["id_documento"] for d in todos) + 1


def adjuntar_documento(
    id_peg: int,
    nombre_archivo: str,
    ruta: str,
    tipo: str,
) -> dict:
    """
    Añade un documento al PEG y actualiza factura_recibida
    automáticamente si el tipo es FACTURA.
    tipo debe ser uno de: FACTURA_PROFORMA, PRESUPUESTO, FACTURA, OTROS
    """
    peg = get_peg_por_id(id_peg)
    if not peg:
        raise ValueError("PEG no encontrado")

    from datetime import date
    doc = {
        "id_documento": _siguiente_id_documento(),
        "id_peg": id_peg,
        "tipo": tipo,
        "nombre_archivo": nombre_archivo,
        "ruta": ruta,
        "fecha_subida": date.today().isoformat(),
    }
    if "documentos" not in peg:
        peg["documentos"] = []
    peg["documentos"].append(doc)

    # Activar factura_recibida automáticamente
    if tipo == "FACTURA":
        peg["factura_recibida"] = True

    return doc


def eliminar_documento(id_peg: int, id_documento: int) -> bool:
    """
    Elimina un documento. Si era el único de tipo FACTURA,
    desactiva factura_recibida del PEG.
    """
    peg = get_peg_por_id(id_peg)
    if not peg:
        return False
    docs = peg.get("documentos", [])
    peg["documentos"] = [d for d in docs if d["id_documento"] != id_documento]

    # Recalcular factura_recibida
    tiene_factura = any(d["tipo"] == "FACTURA" for d in peg["documentos"])
    peg["factura_recibida"] = tiene_factura
    return True


def tiene_documentos(id_peg: int) -> bool:
    peg = get_peg_por_id(id_peg)
    if not peg:
        return False
    return len(peg.get("documentos", [])) > 0


def get_pegs_count_por_estado(estado: str, id_servicio: int = None) -> int:
    estado_obj = next((e for e in _estados if e["codigo"] == estado), None)
    if not estado_obj:
        return 0
    id_estado = estado_obj["id_peg_estado"]
    return sum(
        1 for p in _pegs
        if p.get("id_peg_estado") == id_estado
        and (id_servicio is None or p.get("id_servicio") == id_servicio)
    )
