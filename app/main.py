import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from typing import Optional
from app.core.auth import get_usuario_actual, NoAutenticado
from app.core.templating import templates
from app.routers import servicios, proveedores, pegs, remesas, solicitudes as solicitudes_router
from app.routers import gastos as gastos_router
from app.routers import remesas_directas as remesas_directas_router
from app.services import pegs_service
from app.routers import auth as auth_router
from app.routers import bancos as bancos_router
from app.routers import usuarios as usuarios_router
from app.routers import adjuntos as adjuntos_router
from app.routers import admin as admin_router

os.makedirs("uploads/pegs", exist_ok=True)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

app.include_router(auth_router.router)
app.include_router(servicios.router)
app.include_router(proveedores.router)
app.include_router(pegs.router)
app.include_router(remesas.router)
from app import cuaderno34
app.include_router(cuaderno34.router)
app.include_router(bancos_router.router)
app.include_router(usuarios_router.router)
app.include_router(adjuntos_router.router)
app.include_router(admin_router.router)
app.include_router(solicitudes_router.router)
app.include_router(gastos_router.router)
app.include_router(remesas_directas_router.router)


@app.exception_handler(NoAutenticado)
async def no_autenticado_handler(request: Request, exc: NoAutenticado):
    return RedirectResponse(url="/login", status_code=302)


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, servicio: Optional[int] = None):
    usuario = get_usuario_actual(request)
    if not usuario:
        return RedirectResponse(url="/login", status_code=302)
    from app.services.pegs_service import obtener_servicios
    from app.services.gastos_service import listar_gastos
    from app.services.remesas_directas_service import listar_remesas
    kpis = pegs_service.obtener_kpis_dashboard(usuario, id_servicio_filtro=servicio)
    return templates.TemplateResponse(
        request=request,
        name="inicio.html",
        context={
            "app_name": settings.APP_NAME,
            "usuario": usuario,
            "kpis": kpis,
            "servicios": obtener_servicios(),
            "filtro_servicio": servicio,
            "gastos_resumen": listar_gastos(),
            "remesas_directas_resumen": listar_remesas(),
        },
    )


@app.get("/salud")
def salud():
    return {"estado": "correcto"}
