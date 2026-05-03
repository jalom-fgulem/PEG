"""
Registro central de módulos opcionales de SGPEG.

El ADMIN siempre tiene acceso a todos los módulos.
La visibilidad de cada módulo para GESTOR_ECONOMICO se controla con visible_ge.
"""

from typing import Optional

# ── Registro de módulos ───────────────────────────────────────────────────────
# Añadir aquí cada módulo opcional que deba controlarse desde el panel admin.

MODULOS: dict[str, dict] = {
    "ingresos": {
        "key":         "ingresos",
        "label":       "Ingresos",
        "descripcion": (
            "Importación de Excel y generación de SUENLACE.DAT para facturas "
            "y cobros emitidos por los servicios FGULEM (Hospital, Colegio, MULE, Podología)."
        ),
        "url":         "/ingresos/",
        "icono":       "📥",
        "visible_ge":  True,   # visible para GESTOR_ECONOMICO; ADMIN siempre lo ve
        "etiqueta":    "BETA", # BETA | PRODUCCION
    },
}


# ── API pública ───────────────────────────────────────────────────────────────

def listar_modulos() -> list[dict]:
    return list(MODULOS.values())


def obtener_modulo(key: str) -> Optional[dict]:
    return MODULOS.get(key)


def es_visible(key: str, rol: str) -> bool:
    """
    Devuelve True si el módulo debe mostrarse al rol indicado.
    ADMIN siempre ve todo; GESTOR_ECONOMICO respeta el flag visible_ge.
    """
    if rol == "ADMIN":
        return True
    mod = MODULOS.get(key)
    if not mod:
        return False
    if rol == "GESTOR_ECONOMICO":
        return bool(mod.get("visible_ge", False))
    return False


def toggle_visibilidad_ge(key: str) -> bool:
    """Invierte visible_ge del módulo. Devuelve el nuevo estado."""
    mod = MODULOS.get(key)
    if not mod:
        raise KeyError(f"Módulo '{key}' no existe")
    mod["visible_ge"] = not mod["visible_ge"]
    return mod["visible_ge"]


def set_visibilidad_ge(key: str, visible: bool):
    mod = MODULOS.get(key)
    if not mod:
        raise KeyError(f"Módulo '{key}' no existe")
    mod["visible_ge"] = visible
