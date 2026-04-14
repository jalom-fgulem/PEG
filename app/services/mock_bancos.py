from typing import List, Dict, Any
from datetime import datetime

# Nombre y CIF del ordenante siempre fijos
ORDENANTE_NOMBRE = "FUNDACIÓN GENERAL DE LA UNIVERSIDAD DE LEÓN"
ORDENANTE_CIF = "G24356644"

_bancos: List[Dict[str, Any]] = [
    {
        "id_banco": 1,
        "alias": "Cuenta principal CaixaBank",
        "iban": "ES9121000418450200051332",
        "bic": "CAIXESBBXXX",
        "sufijo_ordenante": "001",
        "activa": True,
        "fecha_alta": "2024-01-01",
    },
    {
        "id_banco": 2,
        "alias": "Cuenta secundaria Santander",
        "iban": "ES6000491500051234567892",
        "bic": "BSCHESMMXXX",
        "sufijo_ordenante": "002",
        "activa": True,
        "fecha_alta": "2024-01-01",
    },
]

_next_id_banco = 3


def listar_bancos(solo_activas: bool = False) -> List[Dict[str, Any]]:
    if solo_activas:
        return [b for b in _bancos if b["activa"]]
    return list(_bancos)


def obtener_banco(id_banco: int) -> Dict[str, Any] | None:
    return next((b for b in _bancos if b["id_banco"] == id_banco), None)


def crear_banco(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id_banco
    nuevo = {**datos, "id_banco": _next_id_banco, "fecha_alta": datetime.now().strftime("%Y-%m-%d"), "activa": True}
    _bancos.append(nuevo)
    _next_id_banco += 1
    return nuevo


def actualizar_banco(id_banco: int, datos: Dict[str, Any]) -> Dict[str, Any] | None:
    banco = obtener_banco(id_banco)
    if not banco:
        return None
    banco.update(datos)
    return banco


def desactivar_banco(id_banco: int) -> bool:
    banco = obtener_banco(id_banco)
    if not banco:
        return False
    banco["activa"] = False
    return True
