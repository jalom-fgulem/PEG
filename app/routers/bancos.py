from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.templating import templates
from app.core.auth import get_usuario_actual, require_rol
from app.services import mock_bancos

router = APIRouter(prefix="/bancos", tags=["Bancos"])


@router.get("/", response_class=HTMLResponse)
def listar_bancos(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    items = mock_bancos.listar_bancos()
    return templates.TemplateResponse(request=request, name="bancos/listado.html", context={
        "usuario": usuario,
        "items": items,
        "ordenante_nombre": mock_bancos.ORDENANTE_NOMBRE,
        "ordenante_cif": mock_bancos.ORDENANTE_CIF,
    })


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo_banco(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    return templates.TemplateResponse(request=request, name="bancos/formulario.html", context={
        "usuario": usuario,
        "banco": None,
        "accion": "crear",
    })


@router.post("/nuevo")
def crear_banco(
    request: Request,
    alias: str = Form(...),
    iban: str = Form(...),
    bic: str = Form(""),
    sufijo_ordenante: str = Form(...),
    cuenta_contable: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_bancos.crear_banco({
        "alias": alias.strip(),
        "iban": iban.strip().upper(),
        "bic": bic.strip().upper(),
        "sufijo_ordenante": sufijo_ordenante.strip(),
        "cuenta_contable": cuenta_contable.strip(),
    })
    return RedirectResponse(url="/bancos/?msg=Cuenta+bancaria+creada+correctamente&msg_type=success", status_code=303)


@router.get("/{id_banco}/editar", response_class=HTMLResponse)
def formulario_editar_banco(request: Request, id_banco: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    banco = mock_bancos.obtener_banco(id_banco)
    if not banco:
        return RedirectResponse(url="/bancos/", status_code=302)
    return templates.TemplateResponse(request=request, name="bancos/formulario.html", context={
        "usuario": usuario,
        "banco": banco,
        "accion": "editar",
    })


@router.post("/{id_banco}/editar")
def editar_banco(
    request: Request,
    id_banco: int,
    alias: str = Form(...),
    iban: str = Form(...),
    bic: str = Form(""),
    sufijo_ordenante: str = Form(...),
    cuenta_contable: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_bancos.actualizar_banco(id_banco, {
        "alias": alias.strip(),
        "iban": iban.strip().upper(),
        "bic": bic.strip().upper(),
        "sufijo_ordenante": sufijo_ordenante.strip(),
        "cuenta_contable": cuenta_contable.strip(),
    })
    return RedirectResponse(url="/bancos/?msg=Cuenta+actualizada+correctamente&msg_type=success", status_code=303)


@router.post("/{id_banco}/desactivar")
def desactivar_banco(request: Request, id_banco: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_bancos.desactivar_banco(id_banco)
    return RedirectResponse(url="/bancos/?msg=Cuenta+desactivada&msg_type=success", status_code=303)
