from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from app.core.templating import templates
from app.core.auth import get_usuario_actual, require_rol
from app.services import mock_servicios, mock_proyectos, mock_bancos

router = APIRouter(prefix="/servicios", tags=["Servicios"])


# ─── SERVICIOS ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def listar_servicios(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    items = mock_servicios.listar_servicios()
    bancos = {b["id_banco"]: b for b in mock_bancos.listar_bancos()}
    proyectos_por_servicio = {
        s["id_servicio"]: mock_proyectos.listar_proyectos(id_servicio=s["id_servicio"])
        for s in items
    }
    return templates.TemplateResponse(request=request, name="servicios/listado.html", context={
        "usuario": usuario,
        "items": items,
        "bancos": bancos,
        "proyectos_por_servicio": proyectos_por_servicio,
    })


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo_servicio(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    bancos = mock_bancos.listar_bancos(solo_activas=True)
    return templates.TemplateResponse(request=request, name="servicios/formulario.html", context={
        "usuario": usuario,
        "servicio": None,
        "bancos": bancos,
        "accion": "crear",
    })


@router.post("/nuevo")
def crear_servicio(
    request: Request,
    codigo: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(""),
    analitica_nivel_1: int = Form(...),
    id_banco_defecto: Optional[int] = Form(None),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    nuevo = mock_servicios.crear_servicio({
        "codigo": codigo.strip().upper(),
        "nombre": nombre.strip(),
        "descripcion": descripcion.strip(),
        "analitica_nivel_1": analitica_nivel_1,
        "id_banco_defecto": id_banco_defecto,
    })
    return RedirectResponse(url=f"/servicios/{nuevo['id_servicio']}?msg=Servicio+creado+correctamente&msg_type=success", status_code=303)


@router.get("/{id_servicio}", response_class=HTMLResponse)
def detalle_servicio(request: Request, id_servicio: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    servicio = mock_servicios.obtener_servicio(id_servicio)
    if not servicio:
        return RedirectResponse(url="/servicios/", status_code=302)
    proyectos = mock_proyectos.listar_proyectos(id_servicio=id_servicio)
    banco_defecto = mock_bancos.obtener_banco(servicio["id_banco_defecto"]) if servicio.get("id_banco_defecto") else None
    return templates.TemplateResponse(request=request, name="servicios/detalle.html", context={
        "usuario": usuario,
        "servicio": servicio,
        "proyectos": proyectos,
        "banco_defecto": banco_defecto,
    })


@router.get("/{id_servicio}/editar", response_class=HTMLResponse)
def formulario_editar_servicio(request: Request, id_servicio: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    servicio = mock_servicios.obtener_servicio(id_servicio)
    if not servicio:
        return RedirectResponse(url="/servicios/", status_code=302)
    bancos = mock_bancos.listar_bancos(solo_activas=True)
    return templates.TemplateResponse(request=request, name="servicios/formulario.html", context={
        "usuario": usuario,
        "servicio": servicio,
        "bancos": bancos,
        "accion": "editar",
    })


@router.post("/{id_servicio}/editar")
def editar_servicio(
    request: Request,
    id_servicio: int,
    codigo: str = Form(...),
    nombre: str = Form(...),
    descripcion: str = Form(""),
    analitica_nivel_1: int = Form(...),
    id_banco_defecto: Optional[int] = Form(None),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    mock_servicios.actualizar_servicio(id_servicio, {
        "codigo": codigo.strip().upper(),
        "nombre": nombre.strip(),
        "descripcion": descripcion.strip(),
        "analitica_nivel_1": analitica_nivel_1,
        "id_banco_defecto": id_banco_defecto,
    })
    return RedirectResponse(url=f"/servicios/{id_servicio}?msg=Servicio+actualizado&msg_type=success", status_code=303)


@router.post("/{id_servicio}/desactivar")
def desactivar_servicio(request: Request, id_servicio: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_servicios.desactivar_servicio(id_servicio)
    return RedirectResponse(url="/servicios/?msg=Servicio+desactivado&msg_type=success", status_code=303)


@router.post("/{id_servicio}/toggle-autorizacion")
def toggle_autorizacion(request: Request, id_servicio: int):
    """Activa / desactiva requiere_autorizacion. Solo ADMIN."""
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    servicio = mock_servicios.obtener_servicio(id_servicio)
    if not servicio:
        return RedirectResponse(url="/servicios/", status_code=302)
    nuevo_valor = not servicio.get("requiere_autorizacion", False)
    mock_servicios.actualizar_servicio(id_servicio, {"requiere_autorizacion": nuevo_valor})
    estado_txt = "activada" if nuevo_valor else "desactivada"
    return RedirectResponse(
        url=f"/servicios/{id_servicio}?msg=Autorización+previa+{estado_txt}&msg_type=success",
        status_code=303,
    )


# ─── PROYECTOS ────────────────────────────────────────────────────────────────

@router.get("/{id_servicio}/proyectos/nuevo", response_class=HTMLResponse)
def formulario_nuevo_proyecto(request: Request, id_servicio: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    servicio = mock_servicios.obtener_servicio(id_servicio)
    if not servicio:
        return RedirectResponse(url="/servicios/", status_code=302)
    return templates.TemplateResponse(request=request, name="servicios/proyecto_formulario.html", context={
        "usuario": usuario,
        "servicio": servicio,
        "proyecto": None,
        "accion": "crear",
    })


@router.post("/{id_servicio}/proyectos/nuevo")
def crear_proyecto(
    request: Request,
    id_servicio: int,
    nombre: str = Form(...),
    analitica_nivel_2: int = Form(...),
    cuenta_gasto: str = Form(""),
    cuenta_iva_soportado: str = Form(""),
    cuenta_tesoreria: str = Form(""),
    cuenta_proveedor: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    mock_proyectos.crear_proyecto({
        "id_servicio": id_servicio,
        "nombre": nombre.strip(),
        "analitica_nivel_2": analitica_nivel_2,
        "cuenta_gasto": cuenta_gasto.strip(),
        "cuenta_iva_soportado": cuenta_iva_soportado.strip(),
        "cuenta_tesoreria": cuenta_tesoreria.strip(),
        "cuenta_proveedor": cuenta_proveedor.strip(),
    })
    return RedirectResponse(url=f"/servicios/{id_servicio}?msg=Proyecto+creado+correctamente&msg_type=success", status_code=303)


@router.get("/{id_servicio}/proyectos/{id_proyecto}/editar", response_class=HTMLResponse)
def formulario_editar_proyecto(request: Request, id_servicio: int, id_proyecto: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    servicio = mock_servicios.obtener_servicio(id_servicio)
    proyecto = mock_proyectos.obtener_proyecto(id_proyecto)
    if not servicio or not proyecto:
        return RedirectResponse(url="/servicios/", status_code=302)
    return templates.TemplateResponse(request=request, name="servicios/proyecto_formulario.html", context={
        "usuario": usuario,
        "servicio": servicio,
        "proyecto": proyecto,
        "accion": "editar",
    })


@router.post("/{id_servicio}/proyectos/{id_proyecto}/editar")
def editar_proyecto(
    request: Request,
    id_servicio: int,
    id_proyecto: int,
    nombre: str = Form(...),
    analitica_nivel_2: int = Form(...),
    cuenta_gasto: str = Form(""),
    cuenta_iva_soportado: str = Form(""),
    cuenta_tesoreria: str = Form(""),
    cuenta_proveedor: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    mock_proyectos.actualizar_proyecto(id_proyecto, {
        "nombre": nombre.strip(),
        "analitica_nivel_2": analitica_nivel_2,
        "cuenta_gasto": cuenta_gasto.strip(),
        "cuenta_iva_soportado": cuenta_iva_soportado.strip(),
        "cuenta_tesoreria": cuenta_tesoreria.strip(),
        "cuenta_proveedor": cuenta_proveedor.strip(),
    })
    return RedirectResponse(url=f"/servicios/{id_servicio}?msg=Proyecto+actualizado&msg_type=success", status_code=303)


@router.post("/{id_servicio}/proyectos/{id_proyecto}/desactivar")
def desactivar_proyecto(request: Request, id_servicio: int, id_proyecto: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_proyectos.desactivar_proyecto(id_proyecto)
    return RedirectResponse(url=f"/servicios/{id_servicio}?msg=Proyecto+desactivado&msg_type=success", status_code=303)
