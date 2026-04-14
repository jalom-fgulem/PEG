from typing import Optional
from fastapi import Request, Depends, HTTPException
from app.services import mock_usuarios


class NoAutenticado(Exception):
    pass


ROLES_COMPAT = {
    "SOLICITANTE": "GESTOR_SERVICIO",
    "GESTOR":      "GESTOR_ECONOMICO",
    "SUPERADMIN":  "ADMIN",
}


def autenticar(username: str, password: str) -> Optional[dict]:
    return mock_usuarios.verificar_password(username, password)


def get_usuario_actual(request: Request) -> Optional[dict]:
    username = request.session.get("username")
    if not username:
        raise NoAutenticado()
    usuario = mock_usuarios.obtener_por_username(username)
    if not usuario:
        request.session.clear()
        raise NoAutenticado()
    if usuario["rol"] in ROLES_COMPAT:
        usuario = {**usuario, "rol": ROLES_COMPAT[usuario["rol"]]}
    return usuario


def require_login(request: Request) -> dict:
    usuario = get_usuario_actual(request)
    if not usuario:
        raise NoAutenticado()
    return usuario


def require_rol(*roles_permitidos: str):
    def check(usuario: dict = Depends(require_login)) -> dict:
        if usuario["rol"] not in roles_permitidos:
            raise HTTPException(status_code=403, detail="Sin permisos suficientes")
        return usuario
    return check
