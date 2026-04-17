from typing import List, Dict, Any, Optional
import hashlib


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


_usuarios: List[Dict[str, Any]] = [
    {
        "id_usuario": 1,
        "username": "hv.gestor_servicio",
        "password_hash": _hash_password("1234"),
        "nombre": "Gestor",
        "apellidos": "H. Veterinario",
        "rol": "GESTOR_SERVICIO",
        "id_servicio": 1,
        "servicios_ids": [1],
        "email": "hv.gestor@fgulem.es",
        "activo": True,
    },
    {
        "id_usuario": 2,
        "username": "ci.gestor_servicio",
        "password_hash": _hash_password("1234"),
        "nombre": "Gestor",
        "apellidos": "C. Idiomas",
        "rol": "GESTOR_SERVICIO",
        "id_servicio": 2,
        "servicios_ids": [2],
        "email": "ci.gestor@fgulem.es",
        "activo": True,
    },
    {
        "id_usuario": 3,
        "username": "gestor01",
        "password_hash": _hash_password("1234"),
        "nombre": "Gestor Económico",
        "apellidos": "FGULEM",
        "rol": "GESTOR_ECONOMICO",
        "id_servicio": None,
        "servicios_ids": [],
        "email": "gestor01@fgulem.es",
        "activo": True,
    },
    {
        "id_usuario": 4,
        "username": "admin01",
        "password_hash": _hash_password("1234"),
        "nombre": "Administrador",
        "apellidos": "FGULEM",
        "rol": "ADMIN",
        "id_servicio": None,
        "servicios_ids": [],
        "email": "admin01@fgulem.es",
        "activo": True,
    },
    {
        "id_usuario": 5,
        "username": "dp.gestor_servicio",
        "password_hash": _hash_password("1234"),
        "nombre": "Gestor",
        "apellidos": "Desarrollo Profesional",
        "rol": "GESTOR_SERVICIO",
        "id_servicio": 3,
        "servicios_ids": [3],
        "email": "dp.gestor@fgulem.es",
        "activo": True,
    },
]

_next_id = 6


def _nombre_completo(u: Dict[str, Any]) -> str:
    return f"{u['nombre']} {u['apellidos']}"


def listar_usuarios(solo_activos: bool = False) -> List[Dict[str, Any]]:
    result = list(_usuarios)
    if solo_activos:
        result = [u for u in result if u["activo"]]
    return [_enriquecer(u) for u in result]


def obtener_usuario(id_usuario: int) -> Dict[str, Any] | None:
    u = next((u for u in _usuarios if u["id_usuario"] == id_usuario), None)
    return _enriquecer(u) if u else None


def obtener_por_username(username: str) -> Dict[str, Any] | None:
    u = next((u for u in _usuarios if u["username"] == username), None)
    return _enriquecer(u) if u else None


def _enriquecer(u: Dict[str, Any]) -> Dict[str, Any]:
    return {**u, "nombre_completo": _nombre_completo(u)}


def verificar_password(username: str, password: str) -> Dict[str, Any] | None:
    u = next((u for u in _usuarios if u["username"] == username and u["activo"]), None)
    if u and u["password_hash"] == _hash_password(password):
        return _enriquecer(u)
    return None


def crear_usuario(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id
    nuevo = {
        **datos,
        "id_usuario": _next_id,
        "password_hash": _hash_password(datos.get("password", "1234")),
        "activo": True,
        "servicios_ids": datos.get("servicios_ids", []),
    }
    nuevo.pop("password", None)
    _usuarios.append(nuevo)
    _next_id += 1
    return _enriquecer(nuevo)


def actualizar_usuario(id_usuario: int, datos: Dict[str, Any]) -> Dict[str, Any] | None:
    u = next((u for u in _usuarios if u["id_usuario"] == id_usuario), None)
    if not u:
        return None
    if "password" in datos:
        u["password_hash"] = _hash_password(datos.pop("password"))
    u.update(datos)
    return _enriquecer(u)


def cambiar_password(id_usuario: int, password_actual: str, password_nueva: str) -> bool:
    u = next((u for u in _usuarios if u["id_usuario"] == id_usuario), None)
    if not u:
        return False
    if u["password_hash"] != _hash_password(password_actual):
        return False
    u["password_hash"] = _hash_password(password_nueva)
    return True


def username_existe(username: str, excluir_id: int | None = None) -> bool:
    return any(
        u["username"] == username and u["id_usuario"] != excluir_id
        for u in _usuarios
    )


def desactivar_usuario(id_usuario: int) -> bool:
    u = next((u for u in _usuarios if u["id_usuario"] == id_usuario), None)
    if not u:
        return False
    u["activo"] = False
    return True


def activar_usuario(id_usuario: int) -> bool:
    u = next((u for u in _usuarios if u["id_usuario"] == id_usuario), None)
    if not u:
        return False
    u["activo"] = True
    return True
