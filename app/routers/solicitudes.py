import os
import shutil
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.auth import require_login, require_rol
from app.core.templating import templates
from app.services import solicitudes_service, mensajes_service, email_service
from app.services.mock_servicios import listar_servicios, obtener_servicio
from app.services.proveedores_service import listar_proveedores, obtener_proveedor
from app.services.pegs_service import (
    get_parametro,
    obtener_datos_formulario as _peg_datos,
)

router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])

_TIPOS_ADJ_SOL = ["PRESUPUESTO", "FACTURA_PROFORMA", "OTRO"]


# ── LISTADO ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def solicitudes_lista(
    request: Request,
    filtro_servicio: Optional[int] = None,
    estado: Optional[str] = None,
    usuario: dict = Depends(require_login),
):
    if usuario["rol"] == "GESTOR_SERVICIO":
        items = solicitudes_service.listar_solicitudes(
            id_servicio=usuario["id_servicio"], estado=estado
        )
    elif filtro_servicio:
        items = solicitudes_service.listar_solicitudes(
            id_servicio=filtro_servicio, estado=estado
        )
    else:
        items = solicitudes_service.listar_solicitudes(estado=estado)

    servicios = listar_servicios(solo_activos=True)
    return templates.TemplateResponse(
        request=request,
        name="solicitudes/lista.html",
        context={
            "items":           items,
            "usuario":         usuario,
            "servicios":       servicios,
            "filtro_servicio": filtro_servicio,
            "filtro_estado":   estado,
        },
    )


# ── NUEVA SOLICITUD — /nueva antes de /{id} ────────────────────────────────────

@router.get("/nueva", response_class=HTMLResponse)
def solicitudes_nueva_get(
    request: Request,
    usuario: dict = Depends(require_login),
):
    todos = listar_servicios(solo_activos=True)
    if usuario["rol"] == "GESTOR_SERVICIO":
        # GS: solo su propio servicio (con o sin autorización obligatoria)
        servicios = [s for s in todos
                     if s["id_servicio"] == usuario["id_servicio"]]
    else:
        # GE / Admin: todos los servicios activos
        servicios = todos

    if not servicios:
        return HTMLResponse(
            "No tienes servicios disponibles para crear solicitudes de autorización.",
            status_code=403,
        )

    datos = _peg_datos()
    return templates.TemplateResponse(
        request=request,
        name="solicitudes/nueva.html",
        context={
            "servicios":   servicios,
            "proveedores": listar_proveedores(),
            "formas_pago": datos["formas_pago"],
            "cuenta_saco": get_parametro("cuenta_saco"),
            "usuario":     usuario,
            "error":       None,
        },
    )


@router.post("/nueva")
async def solicitudes_nueva_post(
    request: Request,
    id_servicio: int = Form(...),
    id_proveedor: int = Form(...),
    concepto: str = Form(...),
    fecha_estimada_gasto: str = Form(...),
    id_forma_pago: int = Form(1),
    iban_proveedor: Optional[str] = Form(None),
    lineas_tipo_iva: List[str] = Form(...),
    lineas_base_imponible: List[str] = Form(...),
    tiene_irpf: Optional[str] = Form(None),
    tipo_irpf: str = Form("0"),
    archivos: List[UploadFile] = File(default=[]),
    tipos_documento: List[str] = Form(default=[]),
    usuario: dict = Depends(require_login),
):
    # GS: solo puede crear en su propio servicio
    if usuario["rol"] == "GESTOR_SERVICIO":
        if id_servicio != usuario["id_servicio"]:
            return HTMLResponse("Sin permisos para crear solicitudes en este servicio", status_code=403)

    # Actualizar IBAN del proveedor si se ha introducido uno nuevo
    iban_limpio = (iban_proveedor or "").strip().upper().replace(" ", "")
    if iban_limpio:
        from app.services.proveedores_service import obtener_proveedor, actualizar_iban
        prov = obtener_proveedor(id_proveedor)
        if prov and not prov.get("iban"):
            actualizar_iban(id_proveedor, iban_limpio)

    # Calcular importes
    lineas = [
        {"tipo_iva": float(t), "base_imponible": float(b)}
        for t, b in zip(lineas_tipo_iva, lineas_base_imponible)
        if b.strip()
    ]
    base_total = sum(l["base_imponible"] for l in lineas)
    iva_total  = sum(
        round(l["base_imponible"] * l["tipo_iva"] * 100) / 10000
        for l in lineas
    )
    _tiene_irpf = tiene_irpf == "on"
    _tipo_irpf  = float(tipo_irpf or "0") if _tiene_irpf else 0.0
    irpf_total  = round(base_total * _tipo_irpf * 100) / 10000 if _tiene_irpf else 0.0
    importe_total = base_total + iva_total - irpf_total

    # Guardar adjuntos en carpeta temporal
    # Parea archivo+tipo por posición, descartar slots vacíos
    pares_adj = [(a, t) for a, t in zip(archivos, tipos_documento) if a.filename]
    rutas_tmp: list[tuple[str, str, str]] = []  # (ruta, nombre, tipo)
    carpeta_tmp = f"media/autorizaciones/tmp_{usuario['id_usuario']}"
    if pares_adj:
        os.makedirs(carpeta_tmp, exist_ok=True)
        for archivo, tipo in pares_adj:
            ruta = f"{carpeta_tmp}/{archivo.filename}"
            with open(ruta, "wb") as f:
                shutil.copyfileobj(archivo.file, f)
            rutas_tmp.append((ruta, archivo.filename, tipo))

    solicitud = solicitudes_service.crear_solicitud(
        id_servicio=id_servicio,
        id_usuario_solicitante=usuario["id_usuario"],
        id_proveedor=id_proveedor,
        importe_estimado=Decimal(str(round(importe_total, 2))),
        concepto=concepto,
        fecha_estimada_gasto=date.fromisoformat(fecha_estimada_gasto),
        lineas=lineas,
        base_imponible=base_total,
        importe_iva=iva_total,
        importe_irpf=irpf_total,
        tiene_irpf=_tiene_irpf,
        tipo_irpf=_tipo_irpf,
        id_forma_pago=id_forma_pago,
    )
    email_service.notificar_solicitud_creada(solicitud, usuario["nombre_completo"])

    id_sol = solicitud["id_solicitud"]
    # Mover adjuntos a carpeta definitiva y registrar en BD
    carpeta_def = f"media/autorizaciones/{id_sol}"
    if rutas_tmp:
        os.makedirs(carpeta_def, exist_ok=True)
        for ruta_tmp, nombre, tipo in rutas_tmp:
            ruta_def = f"{carpeta_def}/{nombre}"
            shutil.move(ruta_tmp, ruta_def)
            solicitudes_service.adjuntar_doc(id_sol, nombre, ruta_def, tipo)
        if os.path.isdir(carpeta_tmp):
            try:
                os.rmdir(carpeta_tmp)
            except OSError:
                pass

    return RedirectResponse(url=f"/solicitudes/{id_sol}", status_code=303)


# ── DETALLE — ruta dinámica al final ───────────────────────────────────────────

@router.get("/{id_solicitud}", response_class=HTMLResponse)
def solicitudes_detalle(
    request: Request,
    id_solicitud: int,
    usuario: dict = Depends(require_login),
):
    solicitud = solicitudes_service.obtener_solicitud(id_solicitud)
    if not solicitud:
        return RedirectResponse(url="/solicitudes/?msg=no_encontrada", status_code=303)

    if usuario["rol"] == "GESTOR_SERVICIO" and solicitud["id_servicio"] != usuario["id_servicio"]:
        return HTMLResponse("Sin permisos para ver esta solicitud", status_code=403)

    return templates.TemplateResponse(
        request=request,
        name="solicitudes/detalle.html",
        context={"solicitud": solicitud, "usuario": usuario},
    )


# ── AUTORIZAR ──────────────────────────────────────────────────────────────────

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
    sol = solicitudes_service.obtener_solicitud_raw(id_solicitud)
    if sol:
        mensajes_service.notif_solicitud_autorizada(sol)
        from app.services.mock_usuarios import obtener_usuario
        gs = obtener_usuario(sol["id_usuario_solicitante"])
        if gs and gs.get("email"):
            email_service.notificar_solicitud_autorizada(sol, gs["email"])
    request.session["flash_success"] = "Solicitud autorizada correctamente"
    return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)


# ── DENEGAR ────────────────────────────────────────────────────────────────────

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
    sol = solicitudes_service.obtener_solicitud_raw(id_solicitud)
    if sol:
        mensajes_service.notif_solicitud_denegada(sol, motivo)
        from app.services.mock_usuarios import obtener_usuario
        gs = obtener_usuario(sol["id_usuario_solicitante"])
        if gs and gs.get("email"):
            email_service.notificar_solicitud_denegada(sol, gs["email"], motivo)
    request.session["flash_success"] = "Solicitud denegada"
    return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)


# ── CONVERTIR EN PEG ───────────────────────────────────────────────────────────

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

    if solicitud["estado_solicitud"] != "AUTORIZADA":
        request.session["flash_error"] = "Solo se puede convertir una solicitud AUTORIZADA"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)

    if solicitud.get("id_peg_generado"):
        request.session["flash_error"] = "Esta solicitud ya tiene un PEG generado"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)

    hoy = date.today()
    lineas_peg = [
        LineaIVA(tipo_iva=l["tipo_iva"], base_imponible=l["base_imponible"])
        for l in (solicitud.get("lineas") or [])
    ] or [LineaIVA(tipo_iva=0.0, base_imponible=float(solicitud["importe_estimado"]))]

    data = PegCrear(
        id_servicio=solicitud["id_servicio"],
        id_proyecto=None,
        id_proveedor=solicitud["id_proveedor"],
        id_peg_tipo=2,  # Presupuesto
        numero_documento=f"SOL-{id_solicitud:04d}",
        fecha_documento=hoy,
        fecha_recepcion=hoy,
        fecha_vencimiento=solicitud.get("fecha_estimada_gasto"),
        descripcion_gasto=solicitud["concepto"],
        observaciones=f"Generado automáticamente desde solicitud de autorización #{id_solicitud}",
        id_forma_pago_prevista=solicitud.get("id_forma_pago") or 1,
        lineas=lineas_peg,
        tiene_irpf=solicitud.get("tiene_irpf", False),
        tipo_irpf=solicitud.get("tipo_irpf", 0.0),
        importe_irpf=float(solicitud.get("importe_irpf", 0.0)),
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


# ── VER ADJUNTO ────────────────────────────────────────────────────────────────

@router.get("/{id_solicitud}/adjuntos/{id_sol_adj}/ver")
def solicitudes_ver_adjunto(
    id_solicitud: int,
    id_sol_adj: int,
    usuario: dict = Depends(require_login),
):
    import mimetypes
    from fastapi.responses import FileResponse
    doc = solicitudes_service.obtener_doc(id_solicitud, id_sol_adj)
    if not doc:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    ruta = doc["ruta"]
    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor")
    mime, _ = mimetypes.guess_type(ruta)
    mime = mime or "application/octet-stream"
    headers = {"Content-Disposition": f'inline; filename="{doc["nombre_archivo"]}"'}
    return FileResponse(path=ruta, media_type=mime, headers=headers)


# ── ELIMINAR ADJUNTO ───────────────────────────────────────────────────────────

@router.post("/{id_solicitud}/adjuntos/{id_sol_adj}/eliminar")
def solicitudes_eliminar_adjunto(
    id_solicitud: int,
    id_sol_adj: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    solicitud = solicitudes_service.obtener_solicitud_raw(id_solicitud)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if solicitud["estado_solicitud"] != "PENDIENTE_AUTORIZACION":
        request.session["flash_error"] = "Solo se pueden eliminar adjuntos de solicitudes pendientes"
        return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)
    ok = solicitudes_service.eliminar_doc(id_solicitud, id_sol_adj)
    if not ok:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    request.session["flash_success"] = "Adjunto eliminado"
    return RedirectResponse(url=f"/solicitudes/{id_solicitud}", status_code=303)
