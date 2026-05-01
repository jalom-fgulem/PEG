from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.auth import get_usuario_actual
from app.core.templating import templates

router = APIRouter(prefix="/ayuda", tags=["Ayuda"])

ROLES_GE = ("GESTOR_ECONOMICO", "ADMIN")
ROLES_ALL = ("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")


def _render(request, name, section, extra=None):
    usuario = get_usuario_actual(request)
    ctx = {"usuario": usuario, "ayuda_section": section}
    if extra:
        ctx.update(extra)
    return templates.TemplateResponse(request=request, name=f"ayuda/{name}", context=ctx)


@router.get("/", response_class=HTMLResponse)
def ayuda_inicio(request: Request):
    return _render(request, "inicio.html", "inicio")


@router.get("/flujo-general", response_class=HTMLResponse)
def ayuda_flujo(request: Request):
    return _render(request, "flujo_general.html", "flujo_general")


@router.get("/pegs", response_class=HTMLResponse)
def ayuda_pegs(request: Request):
    return _render(request, "pegs.html", "pegs")


@router.get("/solicitudes", response_class=HTMLResponse)
def ayuda_solicitudes(request: Request):
    return _render(request, "solicitudes.html", "solicitudes")


@router.get("/proveedores", response_class=HTMLResponse)
def ayuda_proveedores(request: Request):
    return _render(request, "proveedores.html", "proveedores")


@router.get("/validacion", response_class=HTMLResponse)
def ayuda_validacion(request: Request):
    usuario = get_usuario_actual(request)
    if usuario and usuario.get("rol") not in ROLES_GE:
        return RedirectResponse(url="/ayuda/", status_code=302)
    return _render(request, "validacion.html", "validacion")


@router.get("/remesas", response_class=HTMLResponse)
def ayuda_remesas(request: Request):
    usuario = get_usuario_actual(request)
    if usuario and usuario.get("rol") not in ROLES_GE:
        return RedirectResponse(url="/ayuda/", status_code=302)
    return _render(request, "remesas.html", "remesas")


@router.get("/remesas-directas", response_class=HTMLResponse)
def ayuda_remesas_directas(request: Request):
    usuario = get_usuario_actual(request)
    if usuario and usuario.get("rol") not in ROLES_GE:
        return RedirectResponse(url="/ayuda/", status_code=302)
    return _render(request, "remesas_directas.html", "remesas_directas")


@router.get("/movimientos", response_class=HTMLResponse)
def ayuda_movimientos(request: Request):
    usuario = get_usuario_actual(request)
    if usuario and usuario.get("rol") not in ROLES_GE:
        return RedirectResponse(url="/ayuda/", status_code=302)
    return _render(request, "movimientos.html", "movimientos")


@router.get("/administracion", response_class=HTMLResponse)
def ayuda_admin(request: Request):
    usuario = get_usuario_actual(request)
    if usuario and usuario.get("rol") != "ADMIN":
        return RedirectResponse(url="/ayuda/", status_code=302)
    return _render(request, "administracion.html", "administracion")
