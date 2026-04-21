from fastapi.templating import Jinja2Templates
from app.core.config import settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

from app.core.auth import get_usuario_actual  # noqa: E402
from app.services.mock_servicios import obtener_servicio  # noqa: E402


def _menu_counts(usuario):
    if not usuario or usuario.get("rol") not in ("GESTOR_ECONOMICO", "ADMIN"):
        return {"menu_pegs_pendientes": 0, "menu_pegs_incidencias": 0,
                "menu_pegs_en_remesa": 0, "menu_pegs_validados": 0,
                "menu_solicitudes_pendientes": 0}
    from app.services.pegs_service import get_pegs_count_por_estado
    from app.mock_data import SOLICITUDES_AUTORIZACION
    return {
        "menu_pegs_pendientes":        get_pegs_count_por_estado("PENDIENTE"),
        "menu_pegs_incidencias":       get_pegs_count_por_estado("INCIDENCIA"),
        "menu_pegs_en_remesa":         get_pegs_count_por_estado("EN_REMESA"),
        "menu_pegs_validados":         get_pegs_count_por_estado("VALIDADO"),
        "menu_solicitudes_pendientes": sum(
            1 for s in SOLICITUDES_AUTORIZACION
            if s.get("estado_solicitud") == "PENDIENTE_AUTORIZACION"
        ),
    }


templates.env.globals["get_usuario_actual"] = get_usuario_actual
templates.env.globals["obtener_servicio"]    = obtener_servicio
templates.env.globals["menu_counts"]         = _menu_counts
