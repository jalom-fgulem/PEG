from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import get_usuario_actual, require_rol
from app.core.templating import templates
from app.services import pegs_service

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── CUENTAS DE GASTO (grupo 6) ─────────────────────────────────────────────

@router.get("/cuentas-gasto", response_class=HTMLResponse)
def cuentas_gasto_listado(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    cuentas = pegs_service.listar_todas_cuentas_gasto()
    return templates.TemplateResponse(request=request, name="admin/cuentas_gasto.html", context={
        "usuario": usuario,
        "cuentas": cuentas,
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "success"),
    })


@router.post("/cuentas-gasto/nueva")
def cuentas_gasto_crear(
    request: Request,
    codigo: str = Form(...),
    descripcion: str = Form(...),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.crear_cuenta_gasto(codigo, descripcion)
    return RedirectResponse(url="/admin/cuentas-gasto?msg=Cuenta+creada+correctamente&msg_type=success", status_code=303)


@router.post("/cuentas-gasto/{id_cuenta}/editar")
def cuentas_gasto_editar(
    request: Request,
    id_cuenta: int,
    codigo: str = Form(...),
    descripcion: str = Form(...),
    activo: str = Form(default="off"),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.actualizar_cuenta_gasto(id_cuenta, codigo, descripcion, activo == "on")
    return RedirectResponse(url="/admin/cuentas-gasto?msg=Cuenta+actualizada&msg_type=success", status_code=303)


@router.post("/cuentas-gasto/{id_cuenta}/toggle")
def cuentas_gasto_toggle(request: Request, id_cuenta: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.toggle_cuenta_gasto(id_cuenta)
    return RedirectResponse(url="/admin/cuentas-gasto", status_code=303)
