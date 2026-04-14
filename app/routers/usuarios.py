from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from app.core.templating import templates
from app.core.auth import get_usuario_actual, require_rol
from app.services import mock_usuarios, mock_servicios

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

ROLES_DISPONIBLES = ["GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN"]


# ─── PERFIL PROPIO ────────────────────────────────────────────────────────────

@router.get("/mi-perfil", response_class=HTMLResponse)
def mi_perfil(request: Request):
    usuario = get_usuario_actual(request)
    servicios = mock_servicios.listar_servicios()
    servicios_usuario = [s for s in servicios if s["id_servicio"] in usuario.get("servicios_ids", [])]
    return templates.TemplateResponse(request=request, name="usuarios/mi_perfil.html", context={
        "usuario": usuario,
        "servicios_usuario": servicios_usuario,
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type"),
    })


@router.post("/mi-perfil/email")
def actualizar_email(
    request: Request,
    email: str = Form(...),
):
    usuario = get_usuario_actual(request)
    mock_usuarios.actualizar_usuario(usuario["id_usuario"], {"email": email.strip()})
    return RedirectResponse(url="/usuarios/mi-perfil?msg=Email+actualizado+correctamente&msg_type=success", status_code=303)


@router.post("/mi-perfil/password")
def cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirmar: str = Form(...),
):
    usuario = get_usuario_actual(request)
    if password_nueva != password_confirmar:
        return RedirectResponse(url="/usuarios/mi-perfil?msg=Las+contraseñas+no+coinciden&msg_type=error", status_code=303)
    if len(password_nueva) < 6:
        return RedirectResponse(url="/usuarios/mi-perfil?msg=La+contraseña+debe+tener+al+menos+6+caracteres&msg_type=error", status_code=303)
    ok = mock_usuarios.cambiar_password(usuario["id_usuario"], password_actual, password_nueva)
    if not ok:
        return RedirectResponse(url="/usuarios/mi-perfil?msg=La+contraseña+actual+no+es+correcta&msg_type=error", status_code=303)
    return RedirectResponse(url="/usuarios/mi-perfil?msg=Contraseña+cambiada+correctamente&msg_type=success", status_code=303)


# ─── GESTIÓN ADMIN ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def listar_usuarios(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    items = mock_usuarios.listar_usuarios()
    servicios = {s["id_servicio"]: s for s in mock_servicios.listar_servicios()}
    return templates.TemplateResponse(request=request, name="usuarios/listado.html", context={
        "usuario": usuario,
        "items": items,
        "servicios": servicios,
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type"),
    })


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo_usuario(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    servicios = mock_servicios.listar_servicios(solo_activos=True)
    return templates.TemplateResponse(request=request, name="usuarios/formulario.html", context={
        "usuario": usuario,
        "editado": None,
        "servicios": servicios,
        "roles": ROLES_DISPONIBLES,
        "accion": "crear",
    })


@router.post("/nuevo")
def crear_usuario(
    request: Request,
    username: str = Form(...),
    nombre: str = Form(...),
    apellidos: str = Form(...),
    email: str = Form(...),
    rol: str = Form(...),
    password: str = Form(...),
    servicios_ids: list[int] = Form(default=[]),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    if mock_usuarios.username_existe(username):
        servicios = mock_servicios.listar_servicios(solo_activos=True)
        return templates.TemplateResponse(request=request, name="usuarios/formulario.html", context={
            "usuario": usuario,
            "editado": None,
            "servicios": servicios,
            "roles": ROLES_DISPONIBLES,
            "accion": "crear",
            "error": f"El nombre de usuario '{username}' ya existe.",
        })
    mock_usuarios.crear_usuario({
        "username": username.strip().lower(),
        "nombre": nombre.strip(),
        "apellidos": apellidos.strip(),
        "email": email.strip(),
        "rol": rol,
        "password": password,
        "servicios_ids": servicios_ids,
    })
    return RedirectResponse(url="/usuarios/?msg=Usuario+creado+correctamente&msg_type=success", status_code=303)


@router.get("/{id_usuario}/editar", response_class=HTMLResponse)
def formulario_editar_usuario(request: Request, id_usuario: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    editado = mock_usuarios.obtener_usuario(id_usuario)
    if not editado:
        return RedirectResponse(url="/usuarios/", status_code=302)
    servicios = mock_servicios.listar_servicios(solo_activos=True)
    return templates.TemplateResponse(request=request, name="usuarios/formulario.html", context={
        "usuario": usuario,
        "editado": editado,
        "servicios": servicios,
        "roles": ROLES_DISPONIBLES,
        "accion": "editar",
    })


@router.post("/{id_usuario}/editar")
def editar_usuario(
    request: Request,
    id_usuario: int,
    nombre: str = Form(...),
    apellidos: str = Form(...),
    email: str = Form(...),
    rol: str = Form(...),
    servicios_ids: list[int] = Form(default=[]),
    password_nueva: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    datos = {
        "nombre": nombre.strip(),
        "apellidos": apellidos.strip(),
        "email": email.strip(),
        "rol": rol,
        "servicios_ids": servicios_ids,
    }
    if password_nueva.strip():
        if len(password_nueva) < 6:
            editado = mock_usuarios.obtener_usuario(id_usuario)
            servicios = mock_servicios.listar_servicios(solo_activos=True)
            return templates.TemplateResponse(request=request, name="usuarios/formulario.html", context={
                "usuario": usuario,
                "editado": editado,
                "servicios": servicios,
                "roles": ROLES_DISPONIBLES,
                "accion": "editar",
                "error": "La contraseña debe tener al menos 6 caracteres.",
            })
        datos["password"] = password_nueva
    mock_usuarios.actualizar_usuario(id_usuario, datos)
    return RedirectResponse(url=f"/usuarios/?msg=Usuario+actualizado+correctamente&msg_type=success", status_code=303)


@router.post("/{id_usuario}/desactivar")
def desactivar_usuario(request: Request, id_usuario: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    if usuario["id_usuario"] == id_usuario:
        return RedirectResponse(url="/usuarios/?msg=No+puedes+desactivar+tu+propio+usuario&msg_type=error", status_code=303)
    mock_usuarios.desactivar_usuario(id_usuario)
    return RedirectResponse(url="/usuarios/?msg=Usuario+desactivado&msg_type=success", status_code=303)


@router.post("/{id_usuario}/activar")
def activar_usuario(request: Request, id_usuario: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    mock_usuarios.activar_usuario(id_usuario)
    return RedirectResponse(url="/usuarios/?msg=Usuario+activado&msg_type=success", status_code=303)
