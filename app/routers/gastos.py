from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import require_login, require_rol
from app.core.templating import templates
from app.services.gastos_service import (
    listar_gastos,
    obtener_gasto,
    crear_gasto,
    actualizar_estado,
    obtener_lineas_analitica,
    get_tarjetas,
    get_proveedores,
    get_servicios,
    get_usuarios,
    get_analiticas_por_servicio,
)

router = APIRouter(prefix="/gastos", tags=["Gastos"])


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def gastos_listado(
    request: Request,
    tipo: str = "",
    estado: str = "",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    items = listar_gastos(tipo=tipo or None, estado=estado or None)
    proveedores = {p["id_proveedor"]: p for p in get_proveedores()}
    for g in items:
        prov = proveedores.get(g["proveedor_id"])
        g["nombre_proveedor"] = prov["razon_social"] if prov else "—"
    return templates.TemplateResponse(
        request=request,
        name="gastos/listado.html",
        context={
            "usuario": usuario,
            "items": items,
            "filtro_tipo": tipo,
            "filtro_estado": estado,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# NUEVO GASTO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
def gastos_nuevo(
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    return templates.TemplateResponse(
        request=request,
        name="gastos/nuevo.html",
        context={
            "usuario": usuario,
            "proveedores": get_proveedores(),
            "tarjetas": get_tarjetas(),
            "servicios": get_servicios(),
            "usuarios": get_usuarios(),
        },
    )


@router.post("/nuevo")
def gastos_nuevo_post(
    request: Request,
    tipo: str = Form(...),
    proveedor_id: int = Form(...),
    tarjeta_id: str = Form(""),
    empleado_id: str = Form(""),
    fecha_documento: str = Form(...),
    fecha_cargo_real: str = Form(""),
    concepto: str = Form(...),
    referencia_factura: str = Form(""),
    importe_base: float = Form(...),
    porcentaje_iva: float = Form(21.0),
    servicio_id: int = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    importe_iva = round(importe_base * porcentaje_iva / 100, 2)
    importe_total = round(importe_base + importe_iva, 2)
    datos = {
        "tipo": tipo,
        "proveedor_id": proveedor_id,
        "tarjeta_id": int(tarjeta_id) if tarjeta_id else None,
        "empleado_id": int(empleado_id) if empleado_id else None,
        "fecha_documento": fecha_documento,
        "fecha_cargo_real": fecha_cargo_real or None,
        "concepto": concepto.strip(),
        "referencia_factura": referencia_factura.strip() or None,
        "importe_base": importe_base,
        "importe_iva": importe_iva,
        "importe_total": importe_total,
        "irpf": 0.0,
        "servicio_id": servicio_id,
        "lineas_iva": [{"porcentaje_iva": porcentaje_iva, "base": importe_base, "cuota": importe_iva}],
    }
    gasto = crear_gasto(datos, usuario)
    return RedirectResponse(url=f"/gastos/{gasto['id_gasto']}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_gasto}", response_class=HTMLResponse)
def gastos_detalle(
    id_gasto: int,
    request: Request,
    msg: str = "",
    msg_type: str = "success",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    gasto = obtener_gasto(id_gasto)
    if not gasto:
        return HTMLResponse("Gasto no encontrado", status_code=404)

    proveedores = {p["id_proveedor"]: p for p in get_proveedores()}
    tarjetas = {t["id_tarjeta"]: t for t in get_tarjetas()}
    usuarios_map = {u["id_usuario"]: u for u in get_usuarios()}

    proveedor = proveedores.get(gasto["proveedor_id"])
    tarjeta = tarjetas.get(gasto.get("tarjeta_id")) if gasto.get("tarjeta_id") else None
    empleado = usuarios_map.get(gasto.get("empleado_id")) if gasto.get("empleado_id") else None

    analiticas = get_analiticas_por_servicio(gasto["servicio_id"])
    lineas_analitica_completas = obtener_lineas_analitica(id_gasto)

    return templates.TemplateResponse(
        request=request,
        name="gastos/detalle.html",
        context={
            "usuario": usuario,
            "gasto": gasto,
            "proveedor": proveedor,
            "tarjeta": tarjeta,
            "empleado": empleado,
            "analiticas": analiticas,
            "lineas_analitica_completas": lineas_analitica_completas,
            "msg": msg,
            "msg_type": msg_type,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_gasto}/estado")
def gastos_estado(
    id_gasto: int,
    nuevo_estado: str = Form(...),
    analitica_id_1: int = Form(0),
    analitica_porcentaje_1: float = Form(0.0),
    analitica_id_2: int = Form(0),
    analitica_porcentaje_2: float = Form(0.0),
    analitica_id_3: int = Form(0),
    analitica_porcentaje_3: float = Form(0.0),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    lineas = []
    for aid, apct in [
        (analitica_id_1, analitica_porcentaje_1),
        (analitica_id_2, analitica_porcentaje_2),
        (analitica_id_3, analitica_porcentaje_3),
    ]:
        if aid and apct > 0:
            lineas.append({"id_analitica": aid, "porcentaje": apct})

    resultado = actualizar_estado(
        id_gasto,
        nuevo_estado,
        lineas_analitica=lineas if nuevo_estado == "COTEJADO" else None,
    )

    if resultado["ok"]:
        return RedirectResponse(
            url=f"/gastos/{id_gasto}?msg=Estado+actualizado&msg_type=success",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/gastos/{id_gasto}?msg={resultado['error']}&msg_type=error",
        status_code=303,
    )
