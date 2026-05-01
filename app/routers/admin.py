from pathlib import Path

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import get_usuario_actual, require_rol
from app.core.config import settings
from app.core.templating import templates
from app.services import pegs_service

router = APIRouter(prefix="/admin", tags=["Admin"])

_EMAILS_DIR = settings.TEMPLATES_DIR / "emails"

_PLANTILLA_META = {
    "peg_creada.html":          "PEG creada (notificación al solicitante y gestores)",
    "peg_validada.html":        "PEG validada",
    "peg_incidencia.html":      "PEG con incidencia",
    "peg_pagada.html":          "PEG pagada",
    "solicitud_creada.html":    "Solicitud creada (notificación a gestores)",
    "solicitud_autorizada.html":"Solicitud autorizada",
    "solicitud_denegada.html":  "Solicitud denegada",
    "remesa_generada.html":     "Remesa en tramitación bancaria",
    "remesa_cerrada.html":      "Remesa cerrada (pagos ejecutados)",
}


# ── PANEL PRINCIPAL ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def admin_panel(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    return templates.TemplateResponse(request=request, name="admin/panel.html", context={
        "usuario": usuario,
        "tab": "panel",
    })


# ── PLANTILLAS DE CORREO ───────────────────────────────────────────────────────

@router.get("/plantillas-correo", response_class=HTMLResponse)
def plantillas_correo_listado(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    plantillas = [
        {"nombre": nombre, "descripcion": desc}
        for nombre, desc in _PLANTILLA_META.items()
    ]
    return templates.TemplateResponse(request=request, name="admin/plantillas_correo.html", context={
        "usuario": usuario,
        "plantillas": plantillas,
        "tab": "plantillas_correo",
    })


@router.get("/plantillas-correo/{nombre}", response_class=HTMLResponse)
def plantillas_correo_editar(request: Request, nombre: str):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    if nombre not in _PLANTILLA_META:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    contenido = (_EMAILS_DIR / nombre).read_text(encoding="utf-8")
    return templates.TemplateResponse(request=request, name="admin/plantillas_correo_editar.html", context={
        "usuario": usuario,
        "nombre": nombre,
        "descripcion": _PLANTILLA_META[nombre],
        "contenido": contenido,
        "tab": "plantillas_correo",
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "success"),
    })


@router.post("/plantillas-correo/{nombre}")
def plantillas_correo_guardar(request: Request, nombre: str, contenido: str = Form(...)):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    if nombre not in _PLANTILLA_META:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    (_EMAILS_DIR / nombre).write_text(contenido, encoding="utf-8")
    return RedirectResponse(
        url=f"/admin/plantillas-correo/{nombre}?msg=Plantilla+guardada+correctamente&msg_type=success",
        status_code=303,
    )


# ── CUENTAS DE GASTO (grupo 6) ─────────────────────────────────────────────

@router.get("/cuentas-gasto", response_class=HTMLResponse)
def cuentas_gasto_listado(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    cuentas = pegs_service.listar_todas_cuentas_gasto()
    return templates.TemplateResponse(request=request, name="admin/cuentas_gasto.html", context={
        "usuario": usuario,
        "cuentas": cuentas,
        "msg": request.query_params.get("msg"),
        "msg_type": request.query_params.get("msg_type", "success"),
    })


@router.post("/cuentas-gasto/nueva")
def cuentas_gasto_crear(
    request: Request,
    codigo: str = Form(...),
    descripcion: str = Form(...),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.crear_cuenta_gasto(codigo, descripcion)
    return RedirectResponse(url="/admin/cuentas-gasto?msg=Cuenta+creada+correctamente&msg_type=success", status_code=303)


@router.post("/cuentas-gasto/{id_cuenta}/editar")
def cuentas_gasto_editar(
    request: Request,
    id_cuenta: int,
    codigo: str = Form(...),
    descripcion: str = Form(...),
    activo: str = Form(default="off"),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.actualizar_cuenta_gasto(id_cuenta, codigo, descripcion, activo == "on")
    return RedirectResponse(url="/admin/cuentas-gasto?msg=Cuenta+actualizada&msg_type=success", status_code=303)


@router.post("/cuentas-gasto/{id_cuenta}/toggle")
def cuentas_gasto_toggle(request: Request, id_cuenta: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN"])
    pegs_service.toggle_cuenta_gasto(id_cuenta)
    return RedirectResponse(url="/admin/cuentas-gasto", status_code=303)
