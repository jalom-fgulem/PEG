from typing import List, Dict, Any

_proyectos: List[Dict[str, Any]] = [
    {
        "id_proyecto": 1,
        "id_servicio": 1,
        "nombre": "Actividad Clínica",
        "analitica_nivel_2": 1,
        "cuenta_gasto": "6290001",
        "cuenta_iva_soportado": "4720001",
        "cuenta_tesoreria": "5720001",
        "cuenta_proveedor": "400000001",
        "activo": True,
    },
    {
        "id_proyecto": 2,
        "id_servicio": 2,
        "nombre": "Idiomas Modernos",
        "analitica_nivel_2": 1,
        "cuenta_gasto": "6290002",
        "cuenta_iva_soportado": "4720002",
        "cuenta_tesoreria": "5720002",
        "cuenta_proveedor": "400000002",
        "activo": True,
    },
    {
        "id_proyecto": 3,
        "id_servicio": 2,
        "nombre": "Español para Extranjeros",
        "analitica_nivel_2": 2,
        "cuenta_gasto": "6290003",
        "cuenta_iva_soportado": "4720003",
        "cuenta_tesoreria": "5720003",
        "cuenta_proveedor": "400000002",
        "activo": True,
    },
    {
        "id_proyecto": 4,
        "id_servicio": 3,
        "nombre": "Actividad Clínica",
        "analitica_nivel_2": 2,
        "cuenta_gasto": "6290004",
        "cuenta_iva_soportado": "4720004",
        "cuenta_tesoreria": "5720004",
        "cuenta_proveedor": "400000003",
        "activo": True,
    },
]

_next_id_proyecto = 5


def listar_proyectos(id_servicio: int | None = None, solo_activos: bool = False) -> List[Dict[str, Any]]:
    result = list(_proyectos)
    if id_servicio is not None:
        result = [p for p in result if p["id_servicio"] == id_servicio]
    if solo_activos:
        result = [p for p in result if p["activo"]]
    return result


def obtener_proyecto(id_proyecto: int) -> Dict[str, Any] | None:
    return next((p for p in _proyectos if p["id_proyecto"] == id_proyecto), None)


def crear_proyecto(datos: Dict[str, Any]) -> Dict[str, Any]:
    global _next_id_proyecto
    nuevo = {**datos, "id_proyecto": _next_id_proyecto, "activo": True}
    _proyectos.append(nuevo)
    _next_id_proyecto += 1
    return nuevo


def actualizar_proyecto(id_proyecto: int, datos: Dict[str, Any]) -> Dict[str, Any] | None:
    proyecto = obtener_proyecto(id_proyecto)
    if not proyecto:
        return None
    proyecto.update(datos)
    return proyecto


def desactivar_proyecto(id_proyecto: int) -> bool:
    proyecto = obtener_proyecto(id_proyecto)
    if not proyecto:
        return False
    proyecto["activo"] = False
    return True
