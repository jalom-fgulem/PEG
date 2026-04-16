from typing import List, Dict, Any

_servicios: List[Dict[str, Any]] = [
    {
        "id_servicio": 1,
        "codigo": "HVU",
        "nombre": "Hospital Veterinario Universitario",
        "descripcion": "Servicio de atención veterinaria universitaria",
        "activo": True,
        "analitica_nivel_1": 6,
        "id_banco_defecto": 1,
        "gestores_ids": [2],
        "requiere_autorizacion": True,
    },
    {
        "id_servicio": 2,
        "codigo": "CI",
        "nombre": "Centro de Idiomas",
        "descripcion": "Servicio de formación en idiomas",
        "activo": True,
        "analitica_nivel_1": 2,
        "id_banco_defecto": 1,
        "gestores_ids": [3],
        "requiere_autorizacion": False,
    },
    {
        "id_servicio": 3,
        "codigo": "DP",
        "nombre": "Desarrollo Profesional",
        "descripcion": "Servicio de formación y desarrollo profesional",
        "activo": True,
        "analitica_nivel_1": 6,
        "id_banco_defecto": 1,
        "gestores_ids": [],
        "requiere_autorizacion": False,
    },
]

_next_id_servicio = 4


def listar_servicios(solo_activos: bool = False) -> List[Dict[str, Any]]:
    if solo_activos:
        return [s for s in _servicios if s["activo"]]
    return list(_servicios)


def obtener_servicio(id_servicio: int) -> Dict[str, Any] | None:
    return next((s for s in _servicios if s["id_servicio"] == id_servicio), None)


def crear_servicio(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id_servicio
    nuevo = {**datos, "id_servicio": _next_id_servicio, "activo": True, "gestores_ids": []}
    _servicios.append(nuevo)
    _next_id_servicio += 1
    return nuevo


def actualizar_servicio(id_servicio: int, datos: Dict[str, Any]) -> Dict[str, Any] | None:
    servicio = obtener_servicio(id_servicio)
    if not servicio:
        return None
    servicio.update(datos)
    return servicio


def desactivar_servicio(id_servicio: int) -> bool:
    servicio = obtener_servicio(id_servicio)
    if not servicio:
        return False
    servicio["activo"] = False
    return True
