import os
import shutil
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import require_login, require_rol
from app.core.templating import templates
from app.services import solicitudes_service
from app.services.mock_servicios import listar_servicios, obtener_servicio
from app.services.proveedores_service import listar_proveedores, obtener_proveedor

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def solicitudes_lista(
    request: Request,
    usuario: dict = Depends(require_login),
):
    if usuario["rol"] == "GESTOR_SERVICIO":
        items = solicitudes_service.listar_solicitudes(id_servicio=usuario["id_servicio"])
    else:
        items = solicitudes_service.listar_solicitudes()

    return templates.TemplateResponse(
        request=request,
        name="solicitudes/lista.html",
        context={"items": items, "usuario": usuario},
    )


# ──────────────────────────────────────────────────────────────────────────────
# NUEVA SOLICITUD  — literal /nueva antes de /{id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nueva", response_class=HTMLResponse)
def solicitudes_nueva_get(
    request: Request,
    usuario: dict = Depends(require_login),
):
    # Solo servicios que requieren autorización
    servicios = [s for s in listar_servicios(solo_activos=True) if s.get("requiere_autorizacion")]

    # GS: solo su propio servicio (si requiere autorización)
    if usuario["rol"] == "GESTOR_SERVICIO":
        servicios = [s for s in servicios if s["id_servicio"] == usuario["id_servicio"]]

    if not servicios:
        return HTMLResponse(
            "No hay servicios que requieran autorización previa o no tienes acceso.",
            status_code=403,
        )

    proveedores = listar_proveedores()
    # GS: filtrar proveedores de su servicio
    if usuario["rol"] == "GESTOR_SERVICIO":
        id_serv = usuario["id_servicio"]
        proveedores = [p for p in proveedores if id_serv in p.get("servicios", [])]

    return templates.TemplateResponse(
        request=request,
        name="solicitudes/nueva.html",
        context={
            "servicios":   servicios,
            "proveedores": proveedores,
            "usuario":     usuario,
            "error":       None,
        },
    )


@router.post("/nueva")
async def solicitudes_nueva_post(
    request: Request,
    id_servicio: int = Form(...),
    id_proveedor: int = Form(...),
    importe_estimado: str = Form(...),
    concepto: str = Form(...),
    fecha_estimada_gasto: str = Form(...),
    adjunto_1: Optional[UploadFile] = File(default=None),
    adjunto_2: Optional[UploadFile] = File(default=None),
    adjunto_3: Optional[UploadFile] = File(default=None),
    usuario: dict = Depends(require_login),
):
    # Guardia de rol: GS solo para su servicio
    if usuario["rol"] == "GESTOR_SERVICIO" and id_servicio != usuario["id_servicio"]:
        return HTMLResponse("Sin permisos para crear solicitudes en este servicio", status_code=403)

    servicio = obtener_servicio(id_servicio)
    if not servicio or not servicio.get("requiere_autorizacion"):
        return HTMLResponse("El servicio seleccionado no requiere autorización previa", status_code=400)

    # Guardar adjuntos
    def _guardar_adjunto(archivo: Optional[UploadFile], idx: int) -> Optional[str]:
        if not archivo or not archivo.filename:
            return None
        carpeta = f"media/autorizaciones/tmp_{usuario['id_usuario']}"
        os.makedirs(carpeta, exist_ok=True)
        ruta = f"{carpeta}/{archivo.filename}"
        with open(ruta, "wb") as f:
            shutil.copyfileobj(archivo.file, f)
        return ruta

    ruta_1 = _guardar_adjunto(adjunto_1, 1)
    ruta_2 = _guardar_adjunto(adjunto_2, 2)
    ruta_3 = _guardar_adjunto(adjunto_3, 3)

    try:
        importe = Decimal(importe_estimado.replace(",", "."))
    except Exception:
        return HTMLResponse("Importe no válido", status_code=400)

    solicitud = solicitudes_service.crear_solicitud(
        id_servicio=id_servicio,
        id_usuario_solicitante=usuario["id_usuario"],
        id_proveedor=id_proveedor,
        importe_estimado=importe,
        concepto=concepto,
        fecha_estimada_gasto=date.fromisoformat(fecha_estimada_gasto),
        adjunto_1=ruta_1,
        adjunto_2=ruta_2,
        adjunto_3=ruta_3,
    )

    # Mover adjuntos a carpeta definitiva
    id_sol = solicitud["id_solicitud"]
    carpeta_def = f"media/autorizaciones/{id_sol}"
    carpeta_tmp = f"media/autorizaciones/tmp_{usuario['id_usuario']}"
    if os.path.isdir(carpeta_tmp):
        os.makedirs(carpeta_def, exist_ok=True)
        for fname in os.listdir(carpeta_tmp):
            shutil.move(f"{carpeta_tmp}/{fname}", f"{carpeta_def}/{fname}")
        os.rmdir(carpeta_tmp)

    return RedirectResponse(url=f"/solicitudes/{id_sol}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE  — ruta dinámica al final
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_solicitud}", response_class=HTMLResponse)
def solicitudes_detalle(
    request: Request,
    id_solicitud: int,
    usuario: dict = Depends(require_login),
):
    solicitud = solicitudes_service.obtener_solicitud(id_solicitud)
    if not solicitud:
        return RedirectResponse(url="/solicitudes/?msg=no_encontrada", status_code=303)

    # GS solo puede ver las de su servicio
    if usuario["rol"] == "GESTOR_SERVICIO" and solicitud["id_servicio"] != usuario["id_servicio"]:
        return HTMLResponse("Sin permisos para ver esta solicitud", status_code=403)

    return templates.TemplateResponse(
        request=request,
        name="solicitudes/detalle.html",
        context={"solicitud": solicitud, "usuario": usuario},
    )


# ──────────────────────────────────────────────────────────────────────────────
# AUTORIZAR
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_solicitud}/autorizar")
def solicitudes_autorizar(
    id_solicitud: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    resultado = solicitudes_service.autorizar(id_solicitud, usuario["id_usuario"])
    if not resultado:
        request.session["flash_error"] = "No se pudo autorizar (estado incorrecto o no encontrada)"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)
    request.session["flash_success"] = "Solicitud autorizada correctamente"
    return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# CONVERTIR EN PEG
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_solicitud}/convertir-en-peg")
def solicitudes_convertir_en_peg(
    id_solicitud: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    from app.schemas.pegs import PegCrear, LineaIVA
    from app.services import pegs_service

    solicitud = solicitudes_service.obtener_solicitud_raw(id_solicitud)
    if not solicitud:
        request.session["flash_error"] = "Solicitud no encontrada"
        return RedirectResponse(url="/solicitudes/", status_code=303)

    if solicitud["estado"] != "AUTORIZADA":
        request.session["flash_error"] = "Solo se puede convertir una solicitud AUTORIZADA"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)

    if solicitud.get("id_peg_generado"):
        request.session["flash_error"] = "Esta solicitud ya tiene un PEG generado"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)

    hoy = date.today()
    data = PegCrear(
        id_servicio=solicitud["id_servicio"],
        id_proyecto=None,
        id_proveedor=solicitud["id_proveedor"],
        id_peg_tipo=2,                          # Presupuesto
        numero_documento=f"SOL-{id_solicitud:04d}",
        fecha_documento=hoy,
        fecha_recepcion=hoy,
        fecha_vencimiento=solicitud.get("fecha_estimada_gasto"),
        descripcion_gasto=solicitud["concepto"],
        observaciones=f"Generado automáticamente desde solicitud de autorización #{id_solicitud}",
        id_forma_pago_prevista=1,               # Transferencia
        lineas=[LineaIVA(tipo_iva=0.0, base_imponible=float(solicitud["importe_estimado"]))],
        tiene_irpf=False,
        tipo_irpf=0.0,
        importe_irpf=0.0,
        id_analitica=None,
        creado_por=usuario["id_usuario"],
    )
    resultado = pegs_service.crear_peg(data)
    id_peg = resultado["id_peg"]

    solicitudes_service.vincular_peg(id_solicitud, id_peg)

    request.session["flash_success"] = (
        f"PEG {resultado['codigo_peg']} creado a partir de la solicitud #{id_solicitud}"
    )
    return RedirectResponse(url=f"/pegs/{id_peg}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DENEGAR
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_solicitud}/denegar")
def solicitudes_denegar(
    id_solicitud: int,
    request: Request,
    motivo: str = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    if not motivo.strip():
        request.session["flash_error"] = "Debes indicar el motivo de denegación"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)

    resultado = solicitudes_service.denegar(id_solicitud, usuario["id_usuario"], motivo)
    if not resultado:
        request.session["flash_error"] = "No se pudo denegar (estado incorrecto o no encontrada)"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)
    request.session["flash_success"] = "Solicitud denegada"
    return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)
