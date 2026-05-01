from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import require_login
from app.core.templating import templates
from app.services import mock_mensajes, mock_usuarios
from app.services import mensajes_service

router = APIRouter(prefix="/mensajes", tags=["Mensajes"])

_URLS_ENTIDAD = {
    "PEG": "/pegs/{}",
    "SOLICITUD": "/solicitudes/{}",
    "REMESA": "/remesas/{}",
    "REMESA_DIRECTA": "/remesas-directas/{}",
    "GASTO": "/gastos/{}",
}


def _enriquecer(m: dict) -> dict:
    m = dict(m)
    if m.get("id_emisor"):
        u = mock_usuarios.obtener_usuario(m["id_emisor"])
        m["nombre_emisor"] = u["nombre_completo"] if u else "Desconocido"
    else:
        m["nombre_emisor"] = "Sistema"
    tipo = m.get("entidad_tipo")
    eid = m.get("entidad_id")
    tpl = _URLS_ENTIDAD.get(tipo or "")
    m["url_entidad"] = tpl.format(eid) if tpl and eid else None
    return m


@router.get("/", response_class=HTMLResponse)
def bandeja(
    request: Request,
    tab: str = "entrada",
    usuario: dict = Depends(require_login),
):
    uid = usuario["id_usuario"]
    recibidos  = [_enriquecer(m) for m in mock_mensajes.listar_recibidos(uid)]
    enviados   = [_enriquecer(m) for m in mock_mensajes.listar_enviados(uid)]
    archivados = [
        _enriquecer(m)
        for m in mock_mensajes.listar_recibidos(uid, incluir_archivados=True)
        if m["archivado"]
    ]
    return templates.TemplateResponse(
        request=request,
        name="mensajes/bandeja.html",
        context={
            "usuario":    usuario,
            "recibidos":  recibidos,
            "enviados":   enviados,
            "archivados": archivados,
            "tab":        tab,
        },
    )


@router.get("/nuevo", response_class=HTMLResponse)
def nuevo_get(
    request: Request,
    para: Optional[int] = None,
    entidad_tipo: Optional[str] = None,
    entidad_id: Optional[int] = None,
    asunto: Optional[str] = None,
    usuario: dict = Depends(require_login),
):
    otros = [
        u for u in mock_usuarios.listar_usuarios(solo_activos=True)
        if u["id_usuario"] != usuario["id_usuario"]
    ]
    return templates.TemplateResponse(
        request=request,
        name="mensajes/nuevo.html",
        context={
            "usuario":       usuario,
            "usuarios":      otros,
            "para":          para,
            "entidad_tipo":  entidad_tipo or "",
            "entidad_id":    entidad_id,
            "asunto_prefill": asunto or "",
        },
    )


@router.post("/nuevo")
def nuevo_post(
    request: Request,
    id_destinatario: int = Form(...),
    asunto: str = Form(...),
    cuerpo: str = Form(...),
    entidad_tipo: Optional[str] = Form(None),
    entidad_id: Optional[int] = Form(None),
    usuario: dict = Depends(require_login),
):
    mensajes_service.enviar(
        id_emisor=usuario["id_usuario"],
        id_destinatarios=[id_destinatario],
        asunto=asunto.strip(),
        cuerpo=cuerpo.strip(),
        tipo="MANUAL",
        entidad_tipo=entidad_tipo or None,
        entidad_id=entidad_id or None,
    )
    return RedirectResponse(url="/mensajes/?tab=enviados", status_code=303)


@router.get("/{id_mensaje}", response_class=HTMLResponse)
def detalle(
    id_mensaje: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    m = mock_mensajes.obtener_mensaje(id_mensaje)
    if not m:
        return RedirectResponse(url="/mensajes/", status_code=303)
    uid = usuario["id_usuario"]
    if m["id_destinatario"] != uid and m["id_emisor"] != uid:
        return HTMLResponse("Sin permisos para ver este mensaje", status_code=403)
    if m["id_destinatario"] == uid and not m["leido"]:
        mock_mensajes.marcar_leido(id_mensaje, uid)
    return templates.TemplateResponse(
        request=request,
        name="mensajes/detalle.html",
        context={"usuario": usuario, "mensaje": _enriquecer(m)},
    )


@router.post("/{id_mensaje}/archivar")
def archivar(
    id_mensaje: int,
    usuario: dict = Depends(require_login),
):
    mock_mensajes.archivar(id_mensaje, usuario["id_usuario"])
    return RedirectResponse(url="/mensajes/", status_code=303)


@router.post("/{id_mensaje}/eliminar")
def eliminar(
    id_mensaje: int,
    usuario: dict = Depends(require_login),
):
    mock_mensajes.eliminar(id_mensaje, usuario["id_usuario"])
    return RedirectResponse(url="/mensajes/", status_code=303)
