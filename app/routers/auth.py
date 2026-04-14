from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import autenticar
from app.services import mock_usuarios
from app.core.templating import templates

router = APIRouter(tags=["Auth"])


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if request.session.get("username"):
        if not mock_usuarios.obtener_por_username(request.session["username"]):
            request.session.clear()
        else:
            return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"error": None},
    )


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    usuario = autenticar(username.strip(), password)
    if not usuario:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Usuario o contraseña incorrectos", "username": username},
            status_code=401,
        )
    request.session["username"] = usuario["username"]
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
