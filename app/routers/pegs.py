from fastapi import APIRouter, HTTPException, Request, Form, Depends, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional, List
from pydantic import BaseModel

from app.core.auth import require_login, require_rol
from app.services import mock_usuarios
from app.core.templating import templates
from app.schemas.pegs import PegCrear, PegCambioEstado, LineaIVA
from app.services import pegs_service, remesas_service
from app.services import proveedores_service
from app.services import email_service
from app.services.mock_servicios import obtener_servicio as _obtener_servicio

router = APIRouter(prefix="/pegs", tags=["PEGs"])


class _AsignarRemesaBody(BaseModel):
    id_remesa: int


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def pegs_listado(
    request: Request,
    servicio: Optional[int] = None,
    estado: Optional[int] = None,
    q: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    usuario: dict = Depends(require_login),
):
    # SOLICITANTE solo ve los PEGs de su propio servicio
    if usuario["rol"] == "GESTOR_SERVICIO":
        servicio = usuario.get("id_servicio")

    items = pegs_service.listar_pegs(
        id_servicio=servicio,
        id_estado=estado,
        texto=q,
    )
    if proveedor_id:
        items = [i for i in items if i["id_proveedor"] == proveedor_id]
    estados = pegs_service.obtener_estados()
    servicios = pegs_service.obtener_servicios()
    return templates.TemplateResponse(
        request=request,
        name="pegs/listado.html",
        context={
            "items": items,
            "estados": estados,
            "servicios": servicios,
            "filtro_servicio": servicio,
            "filtro_estado": estado,
            "filtro_q": q or "",
            "usuario": usuario,
            "pegs_sin_factura": pegs_service.contar_pagados_sin_factura(),
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# NUEVA PEG  — literal /nuevo debe ir ANTES de /{id_peg}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
def pegs_nuevo(
    request: Request,
    proveedor_id: Optional[int] = None,
    usuario: dict = Depends(require_login),
):
    # Guard: GESTOR_SERVICIO cuyo servicio requiere autorización previa
    if usuario["rol"] == "GESTOR_SERVICIO":
        srv = _obtener_servicio(usuario.get("id_servicio"))
        if srv and srv.get("requiere_autorizacion"):
            request.session["flash_error"] = (
                "Este servicio requiere autorización previa al gasto. "
                "Crea primero una solicitud de autorización."
            )
            return RedirectResponse(url="/solicitudes/nueva", status_code=303)

    datos = pegs_service.obtener_datos_formulario()

    # SOLICITANTE solo puede crear PEGs de su servicio: filtrar la lista
    if usuario["rol"] == "GESTOR_SERVICIO":
        datos["servicios"] = [
            s for s in datos["servicios"] if s["id_servicio"] == usuario["id_servicio"]
        ]

    proveedor_preseleccionado = None
    if proveedor_id:
        proveedor_preseleccionado = pegs_service.obtener_proveedor_json(proveedor_id)
    return templates.TemplateResponse(
        request=request,
        name="pegs/nuevo.html",
        context={**datos, "proveedor_preseleccionado": proveedor_preseleccionado, "usuario": usuario,
                 "cuenta_saco": pegs_service.get_parametro("cuenta_saco")},
    )


@router.post("/nuevo")
async def pegs_nuevo_post(
    request: Request,
    id_servicio: Optional[int] = Form(None),
    id_proyecto: Optional[int] = Form(None),
    id_proveedor: int = Form(...),
    id_peg_tipo: int = Form(...),
    numero_documento: str = Form(...),
    fecha_documento: str = Form(...),
    fecha_recepcion: str = Form(...),
    fecha_vencimiento: Optional[str] = Form(None),
    descripcion_gasto: str = Form(...),
    observaciones: Optional[str] = Form(None),
    id_forma_pago_prevista: int = Form(...),
    lineas_tipo_iva: List[str] = Form(...),
    lineas_base_imponible: List[str] = Form(...),
    tiene_irpf: Optional[str] = Form(None),
    tipo_irpf: str = Form("0"),
    id_analitica: Optional[int] = Form(None),
    archivos: List[UploadFile] = File(default=[]),
    tipos_documento: List[str] = Form(default=[]),
    cuenta_cliente_proveedor: Optional[str] = Form(None),
    iban_proveedor: Optional[str] = Form(None),
    usuario: dict = Depends(require_login),
):
    from datetime import date

    # Si GESTOR_SERVICIO no envía id_servicio (campo hidden ausente), usar el suyo
    if id_servicio is None and usuario["rol"] == "GESTOR_SERVICIO":
        id_servicio = usuario.get("id_servicio")

    # GESTOR_SERVICIO no puede crear PEGs para otros servicios
    if usuario["rol"] == "GESTOR_SERVICIO" and id_servicio != usuario["id_servicio"]:
        return HTMLResponse("Sin permisos para crear PEGs en este servicio", status_code=403)

    # Guard: GESTOR_SERVICIO cuyo servicio requiere autorización previa
    if usuario["rol"] == "GESTOR_SERVICIO":
        srv = _obtener_servicio(id_servicio)
        if srv and srv.get("requiere_autorizacion"):
            request.session["flash_error"] = (
                "Este servicio requiere autorización previa al gasto. "
                "Crea primero una solicitud de autorización."
            )
            return RedirectResponse(url="/solicitudes/nueva", status_code=303)

    # Validar IBAN obligatorio cuando el proveedor no lo tiene registrado
    prov = proveedores_service.obtener_proveedor(id_proveedor)
    iban_limpio = (iban_proveedor or "").strip()
    if prov and not prov.get("iban") and not iban_limpio:
        datos = pegs_service.obtener_datos_formulario()
        if usuario["rol"] == "GESTOR_SERVICIO":
            datos["servicios"] = [
                s for s in datos["servicios"] if s["id_servicio"] == usuario["id_servicio"]
            ]
        return templates.TemplateResponse(
            request=request,
            name="pegs/nuevo.html",
            context={**datos, "proveedor_preseleccionado": prov, "usuario": usuario,
                     "cuenta_saco": pegs_service.get_parametro("cuenta_saco"),
                     "error": "El proveedor no tiene IBAN registrado. Introdúcelo antes de guardar."},
        )

    # Validar que se ha adjuntado al menos un archivo
    archivos_con_nombre = [a for a in archivos if a.filename]
    if not archivos_con_nombre:
        datos = pegs_service.obtener_datos_formulario()
        if usuario["rol"] == "GESTOR_SERVICIO":
            datos["servicios"] = [
                s for s in datos["servicios"] if s["id_servicio"] == usuario["id_servicio"]
            ]
        return templates.TemplateResponse(
            request=request,
            name="pegs/nuevo.html",
            context={**datos, "proveedor_preseleccionado": None, "usuario": usuario,
                     "cuenta_saco": pegs_service.get_parametro("cuenta_saco"),
                     "error": "Debes adjuntar al menos un documento."},
        )

    lineas = [
        LineaIVA(tipo_iva=float(t), base_imponible=float(b))
        for t, b in zip(lineas_tipo_iva, lineas_base_imponible)
        if b.strip()
    ]
    _tiene_irpf = tiene_irpf == "on"
    _tipo_irpf  = float(tipo_irpf or "0") if _tiene_irpf else 0.0
    totales = pegs_service.calcular_totales(
        [l.model_dump() for l in lineas], _tiene_irpf, _tipo_irpf
    )

    data = PegCrear(
        id_servicio=id_servicio,
        id_proyecto=id_proyecto or None,
        id_proveedor=id_proveedor,
        id_peg_tipo=id_peg_tipo,
        numero_documento=numero_documento,
        fecha_documento=date.fromisoformat(fecha_documento),
        fecha_recepcion=date.fromisoformat(fecha_recepcion),
        fecha_vencimiento=date.fromisoformat(fecha_vencimiento) if fecha_vencimiento else None,
        descripcion_gasto=descripcion_gasto,
        observaciones=observaciones or None,
        id_forma_pago_prevista=id_forma_pago_prevista,
        lineas=lineas,
        tiene_irpf=_tiene_irpf,
        tipo_irpf=_tipo_irpf,
        importe_irpf=totales["importe_irpf"],
        id_analitica=id_analitica or None,
        creado_por=usuario["id_usuario"],
    )
    resultado = pegs_service.crear_peg(data)

    # Guardar archivos adjuntos
    import os, shutil
    for archivo, tipo in zip(archivos_con_nombre, tipos_documento):
        carpeta = f"media/pegs/{resultado['id_peg']}"
        os.makedirs(carpeta, exist_ok=True)
        ruta = f"{carpeta}/{archivo.filename}"
        with open(ruta, "wb") as f:
            shutil.copyfileobj(archivo.file, f)
        pegs_service.adjuntar_documento(
            id_peg=resultado["id_peg"],
            nombre_archivo=archivo.filename,
            ruta=ruta,
            tipo=tipo,
        )

    if cuenta_cliente_proveedor and usuario["rol"] in ["GESTOR_ECONOMICO", "ADMIN"]:
        prov_upd = proveedores_service.obtener_proveedor(id_proveedor)
        if prov_upd:
            prov_upd["cuenta_cliente"] = cuenta_cliente_proveedor

    # Guardar IBAN si se ha introducido y el proveedor aún no lo tenía
    if iban_limpio:
        proveedores_service.actualizar_iban(id_proveedor, iban_limpio)

    peg_creada = pegs_service.obtener_peg(resultado["id_peg"])
    email_service.notificar_peg_creada(peg_creada, usuario)

    return RedirectResponse(url=f"/pegs/{resultado['id_peg']}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# AJAX — literal /proveedor/… debe ir ANTES de /{id_peg}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/proveedor/{id_proveedor}/json")
def proveedor_para_peg(
    id_proveedor: int,
    usuario: dict = Depends(require_login),
):
    datos = pegs_service.obtener_proveedor_json(id_proveedor)
    if not datos:
        return JSONResponse({"error": "Proveedor no encontrado"}, status_code=404)
    return JSONResponse(datos)


# ──────────────────────────────────────────────────────────────────────────────
# DOCUMENTOS ADJUNTOS
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_peg}/documentos/subir")
async def peg_subir_documento(
    id_peg: int,
    request: Request,
    tipo: str = Form(...),
    archivo: UploadFile = File(...),
    usuario: dict = Depends(require_rol("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")),
):
    import os, shutil
    tipos_validos = {"FACTURA_PROFORMA", "PRESUPUESTO", "FACTURA", "OTROS"}
    if tipo not in tipos_validos:
        raise HTTPException(status_code=400, detail="Tipo de documento no válido")

    carpeta = f"media/pegs/{id_peg}"
    os.makedirs(carpeta, exist_ok=True)
    ruta = f"{carpeta}/{archivo.filename}"
    with open(ruta, "wb") as f:
        shutil.copyfileobj(archivo.file, f)

    pegs_service.adjuntar_documento(
        id_peg=id_peg,
        nombre_archivo=archivo.filename,
        ruta=ruta,
        tipo=tipo,
    )
    request.session["flash_success"] = "Documento adjuntado correctamente"
    return RedirectResponse(f"/pegs/{id_peg}", status_code=303)


@router.post("/{id_peg}/documentos/{id_documento}/eliminar")
def peg_eliminar_documento(
    id_peg: int,
    id_documento: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")),
):
    eliminado = pegs_service.eliminar_documento(id_peg, id_documento)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    request.session["flash_success"] = "Documento eliminado"
    return RedirectResponse(f"/pegs/{id_peg}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# FECHA DE PAGO — solo GESTOR_ECONOMICO y ADMIN
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_peg}/fecha-pago")
def peg_actualizar_fecha_pago(
    id_peg: int,
    request: Request,
    fecha_pago: str = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        raise HTTPException(status_code=404, detail="PEG no encontrado")
    if peg["id_peg_estado"] != 4:
        raise HTTPException(status_code=400,
            detail="Solo se puede modificar la fecha de pago en estado PAGADO")
    peg["fecha_pago"] = fecha_pago
    request.session["flash_success"] = "Fecha de pago actualizada"
    return RedirectResponse(f"/pegs/{id_peg}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DESCARGA DE DOCUMENTO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_peg}/documentos/{id_documento}/descargar")
def peg_descargar_documento(
    id_peg: int,
    id_documento: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    from fastapi.responses import FileResponse
    import os
    peg = pegs_service.obtener_peg(id_peg)
    if not peg:
        raise HTTPException(status_code=404, detail="PEG no encontrado")
    doc = next(
        (d for d in peg.get("documentos", [])
         if d["id_documento"] == id_documento),
        None
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not os.path.exists(doc["ruta"]):
        raise HTTPException(status_code=404,
            detail="Archivo no encontrado en el servidor")
    return FileResponse(
        path=doc["ruta"],
        filename=doc["nombre_archivo"],
        media_type="application/octet-stream",
    )


# ──────────────────────────────────────────────────────────────────────────────
# NÚMERO DE FACTURA INTERNO
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_peg}/numero-factura")
def peg_actualizar_numero_factura(
    id_peg: int,
    request: Request,
    numero_factura_interno: str = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    from app.services.factura_interna_service import validar_formato
    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        raise HTTPException(status_code=404, detail="PEG no encontrado")
    if peg["id_peg_estado"] != 4:
        raise HTTPException(status_code=400,
            detail="Solo modificable en estado PAGADO")
    numero = numero_factura_interno.strip().upper()
    if numero and not validar_formato(numero):
        request.session["flash_error"] = \
            "Formato incorrecto. Ejemplo válido: F6001ABR"
        return RedirectResponse(f"/pegs/{id_peg}", status_code=303)
    peg["numero_factura_interno"] = numero or None
    request.session["flash_success"] = "Número de factura actualizado"
    return RedirectResponse(f"/pegs/{id_peg}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE  — ruta dinámica /{id_peg} al final
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_peg}", response_class=HTMLResponse)
def peg_detalle(
    request: Request,
    id_peg: int,
    msg: Optional[str] = None,
    msg_type: str = "success",
    usuario: dict = Depends(require_login),
):
    peg = pegs_service.obtener_peg(id_peg)
    if not peg:
        return RedirectResponse(url="/pegs/?msg=PEG+no+encontrada&msg_type=error", status_code=303)

    # SOLICITANTE no puede ver PEGs de otros servicios
    if usuario["rol"] == "GESTOR_SERVICIO" and peg["id_servicio"] != usuario["id_servicio"]:
        return HTMLResponse("Sin permisos para ver esta PEG", status_code=403)

    estados = pegs_service.obtener_estados()
    formas_pago = pegs_service.obtener_datos_formulario()["formas_pago"]
    proveedores = pegs_service.get_proveedores()
    analiticas = pegs_service.obtener_analiticas_servicio(peg["id_servicio"])
    cuentas_gasto = pegs_service.listar_cuentas_gasto()

    # Cuenta grupo 4 del proveedor asociado al PEG (para pre-rellenar en validación)
    proveedor_peg = next((p for p in proveedores if p["id_proveedor"] == peg.get("id_proveedor")), None)
    cuenta_proveedor = (proveedor_peg or {}).get("cuenta_cliente") or ""

    return templates.TemplateResponse(
        request=request,
        name="pegs/detalle.html",
        context={"peg": peg, "estados": estados, "formas_pago": formas_pago, "proveedores": proveedores, "analiticas": analiticas, "cuentas_gasto": cuentas_gasto, "usuario": usuario, "msg": msg, "msg_type": msg_type,
                 "cuenta_saco": pegs_service.get_parametro("cuenta_saco"),
                 "cuenta_proveedor": cuenta_proveedor},
    )


@router.get("/{id_peg}/json")
def peg_detalle_json(
    id_peg: int,
    usuario: dict = Depends(require_login),
):
    peg = pegs_service.obtener_peg(id_peg)
    if not peg:
        return JSONResponse({"error": "PEG no encontrada"}, status_code=404)
    return JSONResponse(peg)


# ──────────────────────────────────────────────────────────────────────────────
# ASIGNAR A REMESA — solo GESTOR_ECONOMICO y ADMIN
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_peg}/asignar-remesa")
def peg_asignar_remesa(
    id_peg: int,
    body: _AsignarRemesaBody,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(body.id_remesa)
    if not remesa:
        return JSONResponse({"ok": False, "error": "Remesa no encontrada"}, status_code=404)
    if remesa["estado"] != "ABIERTA":
        return JSONResponse({"ok": False, "error": "La remesa no está abierta"})

    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        return JSONResponse({"ok": False, "error": "PEG no encontrado"}, status_code=404)
    if peg["id_peg_estado"] != 2:
        return JSONResponse({"ok": False, "error": "El PEG no está en estado Validado"})
    if not peg.get("id_analitica"):
        return JSONResponse({"ok": False, "error": "El PEG no tiene analítica asignada"})
    if peg.get("id_remesa") is not None:
        return JSONResponse({"ok": False, "error": "El PEG ya está en una remesa"})

    pegs_service.asignar_a_remesa(id_peg, body.id_remesa, usuario["nombre_completo"])
    remesas_service.añadir_pago(body.id_remesa, id_peg)
    return JSONResponse({"ok": True})


# ──────────────────────────────────────────────────────────────────────────────
# EDITAR PEG — GESTOR_SERVICIO, GESTOR_ECONOMICO y ADMIN con reglas distintas
# ──────────────────────────────────────────────────────────────────────────────

# Transiciones permitidas por estado origen (id) → destinos válidos (ids)
_TRANSICIONES_GESTOR_ECONOMICO: dict[int, set[int]] = {
    1: {2, 5},   # PENDIENTE  → VALIDADO, INCIDENCIA
    2: {1},      # VALIDADO   → PENDIENTE  (requiere motivo)
    3: {2},      # EN_REMESA  → VALIDADO   (requiere motivo + quita remesa)
    5: {1},      # INCIDENCIA → PENDIENTE
}


@router.post("/{id_peg}/editar")
def peg_editar(
    id_peg: int,
    descripcion_gasto: str = Form(...),
    numero_documento: str = Form(...),
    fecha_documento: str = Form(...),
    fecha_vencimiento: Optional[str] = Form(None),
    observaciones: Optional[str] = Form(None),
    id_forma_pago_prevista: int = Form(...),
    id_proveedor: int = Form(...),
    lineas_tipo_iva: List[str] = Form(...),
    lineas_base_imponible: List[str] = Form(...),
    nuevo_estado: Optional[int] = Form(None),
    motivo_cambio_estado: Optional[str] = Form(None),
    usuario: dict = Depends(require_login),
):
    rol = usuario["rol"]

    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        return RedirectResponse(url="/pegs/?msg=PEG+no+encontrada&msg_type=error", status_code=303)

    if peg["id_peg_estado"] == 4:  # PAGADO — no editable bajo ningún rol
        return HTMLResponse("No se puede editar un PEG en estado PAGADO", status_code=403)

    estado_actual = peg["id_peg_estado"]

    # ── Comprobaciones de acceso por rol ──────────────────────────────────────
    if rol == "GESTOR_SERVICIO":
        if peg["id_servicio"] != usuario["id_servicio"]:
            return HTMLResponse("Sin permisos para editar esta PEG", status_code=403)
        if estado_actual != 1:  # solo PENDIENTE
            return RedirectResponse(
                url=f"/pegs/{id_peg}?msg=Solo+puede+editar+PEGs+en+estado+Pendiente&msg_type=error",
                status_code=303,
            )
        nuevo_estado = None  # GESTOR_SERVICIO no cambia estado

    elif rol == "GESTOR_ECONOMICO":
        if estado_actual not in (1, 5):  # PENDIENTE o INCIDENCIA
            return RedirectResponse(
                url=f"/pegs/{id_peg}?msg=Solo+puede+editar+PEGs+en+estado+Pendiente+o+Incidencia&msg_type=error",
                status_code=303,
            )
        if nuevo_estado is not None:
            permitidos = _TRANSICIONES_GESTOR_ECONOMICO.get(estado_actual, set())
            if nuevo_estado not in permitidos:
                return RedirectResponse(
                    url=f"/pegs/{id_peg}?msg=Transicion+de+estado+no+permitida&msg_type=error",
                    status_code=303,
                )
            # VALIDADO→PENDIENTE y EN_REMESA→VALIDADO requieren motivo
            if estado_actual in (2, 3) and not (motivo_cambio_estado or "").strip():
                return RedirectResponse(
                    url=f"/pegs/{id_peg}?msg=Se+requiere+motivo+para+este+cambio+de+estado&msg_type=error",
                    status_code=303,
                )

    # ADMIN: sin restricciones de estado ni transición

    # ── Construir líneas ──────────────────────────────────────────────────────
    lineas = [
        {"tipo_iva": float(t), "base_imponible": float(b)}
        for t, b in zip(lineas_tipo_iva, lineas_base_imponible)
        if b.strip()
    ]

    campos = {
        "descripcion_gasto":      descripcion_gasto,
        "numero_documento":       numero_documento,
        "fecha_documento":        fecha_documento,
        "fecha_vencimiento":      fecha_vencimiento or None,
        "observaciones":          observaciones or None,
        "id_forma_pago_prevista": id_forma_pago_prevista,
        "id_proveedor":           id_proveedor,
        "lineas":                 lineas,
    }

    resultado = pegs_service.editar_peg(
        id_peg=id_peg,
        campos=campos,
        nuevo_estado_id=nuevo_estado,
        nombre_usuario=usuario["nombre_completo"],
        motivo=motivo_cambio_estado or None,
    )

    if not resultado.get("ok"):
        return RedirectResponse(
            url=f"/pegs/{id_peg}?msg={resultado.get('error', 'Error+al+editar')}&msg_type=error",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/pegs/{id_peg}?msg=Actualizado+correctamente",
        status_code=303,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CAMBIO DE ESTADO — solo GESTOR_ECONOMICO y ADMIN
# ──────────────────────────────────────────────────────────────────────────────

_MSG_PAGADA = "Esta+PEG+está+pagada+y+no+puede+modificarse"


def _guardia_pagado(id_peg: int, usuario: dict) -> Optional[RedirectResponse]:
    """Devuelve RedirectResponse de error si la PEG está PAGADA y el usuario no es ADMIN."""
    if usuario["rol"] == "ADMIN":
        return None
    peg = pegs_service.obtener_peg(id_peg)
    if peg and peg.get("codigo_estado") == "PAGADO":
        return RedirectResponse(
            url=f"/pegs/{id_peg}?msg={_MSG_PAGADA}&msg_type=error",
            status_code=303,
        )
    return None


@router.get("/{id_peg}/analiticas")
def get_analiticas_peg(
    id_peg: int,
    usuario: dict = Depends(require_login),
):
    if usuario["rol"] not in ["GESTOR_ECONOMICO", "ADMIN"]:
        return JSONResponse({"error": "Sin permiso"}, status_code=403)
    peg = pegs_service.obtener_peg(id_peg)
    if not peg:
        return JSONResponse({"error": "No encontrado"}, status_code=404)
    analiticas = pegs_service.obtener_analiticas_servicio(peg["id_servicio"])
    return JSONResponse(analiticas)


@router.post("/{id_peg}/eliminar")
def post_eliminar_peg(
    id_peg: int,
    usuario: dict = Depends(require_login),
):
    if usuario["rol"] not in ["GESTOR_ECONOMICO", "ADMIN"]:
        return RedirectResponse(f"/pegs/{id_peg}?msg=Sin+permiso&msg_type=error", status_code=303)
    resultado = pegs_service.eliminar_peg(id_peg, usuario)
    if resultado["ok"]:
        return RedirectResponse("/pegs/?msg=PEG+eliminado+correctamente", status_code=303)
    else:
        return RedirectResponse(
            f"/pegs/{id_peg}?msg={resultado['error']}&msg_type=error",
            status_code=303,
        )


@router.post("/{id_peg}/validar")
def post_validar_peg(
    id_peg: int,
    id_analitica: int = Form(...),
    observaciones: str = Form(""),
    id_cuenta_gasto: Optional[int] = Form(None),
    cuenta_cliente_proveedor: str = Form(""),
    usuario: dict = Depends(require_login),
):
    if usuario["rol"] not in ["GESTOR_ECONOMICO", "ADMIN"]:
        return RedirectResponse(f"/pegs/{id_peg}?msg=Sin+permiso&msg_type=error", status_code=303)
    if not id_cuenta_gasto:
        return HTMLResponse("Campo obligatorio: cuenta de gasto", status_code=400)
    if not cuenta_cliente_proveedor.strip():
        return HTMLResponse("Campo obligatorio: cuenta del proveedor (cliente A3Con)", status_code=400)
    resultado = pegs_service.validar_peg(
        id_peg, id_analitica, observaciones, usuario,
        id_cuenta_gasto=id_cuenta_gasto,
        cuenta_cliente_proveedor=cuenta_cliente_proveedor,
    )
    if resultado["ok"]:
        return RedirectResponse(f"/pegs/{id_peg}?msg=PEG+validado+correctamente", status_code=303)
    else:
        return RedirectResponse(
            f"/pegs/{id_peg}?msg={resultado['error']}&msg_type=error",
            status_code=303,
        )


@router.post("/{id_peg}/incidencia")
def peg_incidencia(
    id_peg: int,
    comentario: Optional[str] = Form(None),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    if (r := _guardia_pagado(id_peg, usuario)):
        return r
    pegs_service.cambiar_estado_directo(
        id_peg, 5, usuario["nombre_completo"], comentario or "Marcada como incidencia"
    )
    return RedirectResponse(url=f"/pegs/{id_peg}", status_code=303)


@router.post("/{id_peg}/factura-recibida")
def toggle_factura_recibida(
    id_peg: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")),
):
    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        raise HTTPException(status_code=404, detail="PEG no encontrado")
    if peg["id_peg_estado"] != 4:  # solo en PAGADO
        raise HTTPException(status_code=400, detail="Solo se puede modificar en estado PAGADO")
    peg["factura_recibida"] = not peg.get("factura_recibida", False)
    return RedirectResponse(f"/pegs/{id_peg}", status_code=303)


@router.post("/{id_peg}/reabrir")
def peg_reabrir(
    id_peg: int,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    if (r := _guardia_pagado(id_peg, usuario)):
        return r
    pegs_service.cambiar_estado_directo(id_peg, 1, usuario["nombre_completo"], "PEG reabierta como pendiente")
    return RedirectResponse(url=f"/pegs/{id_peg}", status_code=303)


@router.post("/{id_peg}/estado")
def peg_cambiar_estado(
    id_peg: int,
    id_peg_estado_destino: int = Form(...),
    comentario: Optional[str] = Form(None),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    if (r := _guardia_pagado(id_peg, usuario)):
        return r
    cambio = PegCambioEstado(
        id_peg_estado_destino=id_peg_estado_destino,
        comentario=comentario or None,
        realizado_por=usuario["id_usuario"],
    )
    peg_antes = pegs_service.obtener_peg(id_peg)
    ok = pegs_service.cambiar_estado_peg(id_peg, cambio)
    if not ok:
        return JSONResponse({"error": "PEG no encontrada"}, status_code=404)

    # Obtener email del solicitante que creó la PEG
    peg_actual = pegs_service.obtener_peg(id_peg)
    id_creador = peg_actual.get("creado_por")
    creador = mock_usuarios.obtener_usuario(id_creador)
    email_sol = creador["email"] if creador and creador.get("email") else None

    # Despachar notificación según estado destino
    # Estados: 1=PENDIENTE, 2=VALIDADO, 3=EN_REMESA, 4=PAGADO, 5=INCIDENCIA
    if email_sol:
        if id_peg_estado_destino == 2:   # VALIDADO
            email_service.notificar_peg_validada(peg_actual, email_sol)
        elif id_peg_estado_destino == 5:  # INCIDENCIA
            email_service.notificar_peg_incidencia(
                peg_actual, email_sol, comentario or "Se ha registrado una incidencia en su PEG."
            )
        elif id_peg_estado_destino == 4:  # PAGADO
            email_service.notificar_peg_pagada(peg_actual, email_sol)

    return RedirectResponse(url=f"/pegs/{id_peg}", status_code=303)
