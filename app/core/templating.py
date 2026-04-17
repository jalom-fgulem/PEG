from fastapi.templating import Jinja2Templates
from app.core.config import settings

# Instancia única compartida por todos los routers.
# Los globals se registran aquí para que estén disponibles en todas las plantillas.
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# Importación diferida para evitar ciclos: auth → config, templating → auth
from app.core.auth import get_usuario_actual  # noqa: E402
from app.services.mock_servicios import obtener_servicio  # noqa: E402
templates.env.globals["get_usuario_actual"] = get_usuario_actual
templates.env.globals["obtener_servicio"] = obtener_servicio
