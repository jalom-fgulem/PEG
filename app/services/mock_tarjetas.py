from typing import List, Dict, Any
from datetime import datetime

_tarjetas: List[Dict[str, Any]] = [
    {
        "id_tarjeta": 1,
        "alias": "Visa Unicaja",
        "numero": "**** **** **** 4521",
        "entidad": "Unicaja",
        "tipo_tarjeta": "VISA",
        "titular": "FUNDACIÓN GENERAL DE LA UNIVERSIDAD DE LEÓN",
        "activa": True,
        "fecha_alta": "2024-01-01",
        "id_banco": 1,
    },
    {
        "id_tarjeta": 2,
        "alias": "Mastercard Santander",
        "numero": "**** **** **** 8834",
        "entidad": "Santander",
        "tipo_tarjeta": "MASTERCARD",
        "titular": "FUNDACIÓN GENERAL DE LA UNIVERSIDAD DE LEÓN",
        "activa": True,
        "fecha_alta": "2024-01-01",
        "id_banco": 2,
    },
]

_next_id = 3


def listar_tarjetas(solo_activas: bool = False) -> List[Dict[str, Any]]:
    if solo_activas:
        return [t for t in _tarjetas if t["activa"]]
    return list(_tarjetas)


def obtener_tarjeta(id_tarjeta: int) -> Dict[str, Any] | None:
    return next((t for t in _tarjetas if t["id_tarjeta"] == id_tarjeta), None)


def crear_tarjeta(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id
    nueva = {**datos, "id_tarjeta": _next_id, "fecha_alta": datetime.now().strftime("%Y-%m-%d"), "activa": True}
    _tarjetas.append(nueva)
    _next_id += 1
    return nueva
