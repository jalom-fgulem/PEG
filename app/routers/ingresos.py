import urllib.parse
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.auth import require_rol
from app.core.templating import templates
from app.services import ingresos_service as svc
from app.services.modulos_service import es_visible

router = APIRouter(prefix="/ingresos", tags=["Ingresos"])


def _require_ingresos(usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))) -> dict:
    """Bloquea el acceso de GESTOR_ECONOMICO si el módulo está desactivado."""
    if not es_visible("ingresos", usuario["rol"]):
        raise HTTPException(status_code=403, detail="El módulo de Ingresos no está disponible.")
    return usuario

AREAS_LABELS   = svc.LABELS_AREA
PROCESO_LABELS = svc.LABELS_PROCESO


# ── LISTADO ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def ingresos_listado(
    request: Request,
    area: str | None = None,
    estado: str | None = None,
    msg: str | None = None,
    msg_type: str = "success",
    usuario: dict = Depends(_require_ingresos),
):
    lotes = svc.listar_lotes(area=area, estado=estado)
    return templates.TemplateResponse(
        request=request,
        name="ingresos/listado.html",
        context={
            "usuario":       usuario,
            "lotes":         lotes,
            "filtro_area":   area,
            "filtro_estado": estado,
            "areas_labels":  AREAS_LABELS,
            "proceso_labels": PROCESO_LABELS,
            "msg":           msg,
            "msg_type":      msg_type,
        },
    )


# ── IMPORTAR (GET) ────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
def ingresos_importar_form(
    request: Request,
    usuario: dict = Depends(_require_ingresos),
):
    return templates.TemplateResponse(
        request=request,
        name="ingresos/importar.html",
        context={
            "usuario":       usuario,
            "areas_labels":  AREAS_LABELS,
            "proceso_labels": PROCESO_LABELS,
            "config":        svc.CONFIG,
        },
    )


# ── IMPORTAR (POST) ───────────────────────────────────────────────────────────

@router.post("/importar")
async def ingresos_importar_post(
    request: Request,
    area:          str = Form(...),
    tipo_proceso:  str = Form(...),
    destino_a3:    str = Form(...),
    fichero:       UploadFile = File(...),
    usuario: dict = Depends(_require_ingresos),
):
    if not fichero.filename or not fichero.filename.lower().endswith((".xlsx", ".xls")):
        error = urllib.parse.quote("El archivo debe ser .xlsx o .xls")
        return RedirectResponse(
            url=f"/ingresos/importar?msg={error}&msg_type=error", status_code=303
        )

    try:
        file_bytes = await fichero.read()
        lote = svc.procesar_excel(
            file_bytes=file_bytes,
            nombre_fichero_origen=fichero.filename,
            area=area,
            tipo_proceso=tipo_proceso,
            destino_a3=destino_a3,
            usuario_id=usuario.get("id_usuario", 0),
        )
    except ValueError as exc:
        error = urllib.parse.quote(str(exc)[:200])
        return RedirectResponse(
            url=f"/ingresos/importar?msg={error}&msg_type=error", status_code=303
        )
    except Exception as exc:
        error = urllib.parse.quote(f"Error inesperado: {str(exc)[:160]}")
        return RedirectResponse(
            url=f"/ingresos/importar?msg={error}&msg_type=error", status_code=303
        )

    msg = urllib.parse.quote(
        f"Lote generado: {lote['registros_ok']} registros OK, {lote['registros_error']} errores."
    )
    return RedirectResponse(
        url=f"/ingresos/{lote['id_lote']}?msg={msg}&msg_type=success", status_code=303
    )


# ── DETALLE LOTE ──────────────────────────────────────────────────────────────

@router.get("/{id_lote}", response_class=HTMLResponse)
def ingresos_detalle(
    request: Request,
    id_lote: int,
    msg: str | None = None,
    msg_type: str = "success",
    usuario: dict = Depends(_require_ingresos),
):
    lote = svc.obtener_lote(id_lote)
    if not lote:
        return HTMLResponse("Lote no encontrado", status_code=404)
    registros = svc.obtener_registros_lote(id_lote)
    return templates.TemplateResponse(
        request=request,
        name="ingresos/detalle_lote.html",
        context={
            "usuario":       usuario,
            "lote":          lote,
            "registros":     registros,
            "areas_labels":  AREAS_LABELS,
            "proceso_labels": PROCESO_LABELS,
            "msg":           msg,
            "msg_type":      msg_type,
        },
    )


# ── DESCARGAR DAT ─────────────────────────────────────────────────────────────

@router.get("/{id_lote}/descargar")
def ingresos_descargar(
    id_lote: int,
    usuario: dict = Depends(_require_ingresos),
):
    lote = svc.obtener_lote(id_lote)
    if not lote:
        return HTMLResponse("Lote no encontrado", status_code=404)

    dat_content = lote.get("dat_content", "")
    if not dat_content:
        return HTMLResponse("No hay contenido DAT para este lote.", status_code=404)

    svc.marcar_exportado(id_lote)
    filename = lote.get("nombre_fichero_dat", "SUENLACE.DAT")

    return Response(
        content=dat_content.encode("latin-1", errors="replace"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
