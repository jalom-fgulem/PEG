import os
import urllib.parse
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from app.core.auth import require_rol
from app.core.templating import templates
from pathlib import Path

from app.services import mock_bancos, pegs_service, remesas_service
from app.services.factura_interna_service import generar_numero_factura
from app.services.pdf_remesa_service import generar_pdf_remesa
from app.services import historial_remesas_service as historial
from app.services import mensajes_service

# Raíz del proyecto para resolver rutas relativas de PDF
# app/routers/remesas.py → app/routers → app → PEG/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

router = APIRouter(prefix="/remesas", tags=["Remesas"])


# ── NUEVA REMESA ───────────────────────────────────────────────────────────────

@router.get("/nueva", response_class=HTMLResponse)
def remesas_nueva_form(request: Request, usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))):
    bancos = mock_bancos.listar_bancos(solo_activas=True)
    return templates.TemplateResponse(request=request, name="remesas/nueva.html",
        context={"bancos": bancos, "usuario": usuario})

@router.post("/nueva")
def remesas_crear(
    request: Request,
    descripcion: str = Form(...),
    id_banco: int = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    if not descripcion.strip():
        bancos = mock_bancos.listar_bancos(solo_activas=True)
        return templates.TemplateResponse(request=request, name="remesas/nueva.html",
            context={"bancos": bancos, "usuario": usuario, "error": "La descripción es obligatoria."})
    nueva = remesas_service.crear_remesa(
        descripcion=descripcion.strip(),
        id_banco=id_banco,
        id_servicio=1,
        creado_por=usuario["nombre_completo"],
    )
    historial.registrar_evento("RT", nueva["id_remesa"], "CREADA", usuario["nombre_completo"])
    return RedirectResponse(url=f"/remesas/{nueva['id_remesa']}?msg=Remesa+creada+correctamente&msg_type=success", status_code=303)


# ── ELIMINAR REMESA ────────────────────────────────────────────────────────────

@router.post("/{id_remesa}/eliminar")
def remesas_eliminar(
    id_remesa: int,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return RedirectResponse(url="/remesas/?msg=Remesa+no+encontrada&msg_type=error", status_code=303)
    if remesa["estado"] != "ABIERTA":
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg=Solo+se+pueden+eliminar+remesas+abiertas&msg_type=error", status_code=303)
    # Revertir PEGs a VALIDADO
    for pid in remesa.get("pagos", []):
        pegs_service.quitar_de_remesa(pid, usuario["nombre_completo"])
    remesas_service.eliminar_remesa(id_remesa)
    return RedirectResponse(url="/remesas/?msg=Remesa+eliminada.+Los+PEGs+han+vuelto+a+estado+Validado.&msg_type=success", status_code=303)


# ── GENERAR REMESA (ABIERTA → GENERADA) ───────────────────────────────────────

@router.post("/{id_remesa}/generar")
def remesas_generar(
    id_remesa: int,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return RedirectResponse(url="/remesas/?msg=Remesa+no+encontrada&msg_type=error", status_code=303)
    if remesa["estado"] != "ABIERTA":
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg=Solo+se+pueden+generar+remesas+abiertas&msg_type=error", status_code=303)

    # Generar PDF antes de cambiar estado
    pagos = [pegs_service.obtener_peg(pid) for pid in remesa.get("pagos", [])]
    pagos = [p for p in pagos if p]
    try:
        pdf_path = generar_pdf_remesa(remesa, pagos)
        remesas_service.actualizar_pdf_path(id_remesa, pdf_path)
    except Exception as exc:
        msg = urllib.parse.quote(f"Error al generar el PDF: {str(exc)[:120]}")
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg={msg}&msg_type=error", status_code=303)

    remesas_service.cambiar_estado_remesa(id_remesa, "GENERADA")
    historial.registrar_evento("RT", id_remesa, "GENERADA", usuario["nombre_completo"], "Cuaderno 34 generado")
    historial.registrar_evento("RT", id_remesa, "PDF_GENERADO", usuario["nombre_completo"])
    peg_ids = list(remesa.get("pagos", []))
    from app.services import email_service as _email_svc
    _email_svc.notificar_remesa_generada(remesa, peg_ids)
    return RedirectResponse(url=f"/remesas/{id_remesa}?msg=Remesa+generada+y+PDF+creado+correctamente&msg_type=success", status_code=303)


# ── CERRAR REMESA (GENERADA → CERRADA) ────────────────────────────────────────

@router.post("/{id_remesa}/cerrar")
def remesas_cerrar(
    id_remesa: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return HTMLResponse("Remesa no encontrada", status_code=404)
    if remesa["estado"] != "GENERADA":
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg=Debe+generar+el+archivo+bancario+primero&msg_type=error", status_code=303)
    remesas_service.cambiar_estado_remesa(id_remesa, "CERRADA")
    remesa_cerrada = remesas_service.obtener_remesa(id_remesa)
    remesa_cerrada["fecha_cierre"] = datetime.now().strftime("%Y-%m-%d")
    n = 0
    for pid in remesa.get("pagos", []):
        ok = pegs_service.cambiar_estado_directo(pid, 4, usuario["nombre_completo"], f"Pagado mediante remesa {remesa['codigo_remesa']}")
        if ok:
            peg_raw = pegs_service.get_peg_raw(pid)
            if peg_raw is not None:
                peg_raw["fecha_pago"] = remesa_cerrada["fecha_cierre"]
                fecha_dt = datetime.fromisoformat(peg_raw["fecha_pago"])
                peg_raw["numero_factura_interno"] = generar_numero_factura(fecha_dt)
            n += 1

    # Regenerar PDF con estado CERRADA y fecha de cierre real
    try:
        pagos = [pegs_service.obtener_peg(pid) for pid in remesa.get("pagos", [])]
        pagos = [p for p in pagos if p]
        pdf_path = generar_pdf_remesa(remesa_cerrada, pagos)
        remesas_service.actualizar_pdf_path(id_remesa, pdf_path)
    except Exception:
        pass  # No bloquear el cierre si falla la regeneración del PDF

    historial.registrar_evento("RT", id_remesa, "CERRADA", usuario["nombre_completo"],
                               f"{n} PEG{'s' if n != 1 else ''} marcado{'s' if n != 1 else ''} como PAGADO")
    peg_ids_cerrada = list(remesa.get("pagos", []))
    mensajes_service.notif_remesa_cerrada(remesa_cerrada, peg_ids_cerrada)
    from app.services import email_service as _email_svc
    pegs_pagados = [pegs_service.obtener_peg(pid) for pid in peg_ids_cerrada]
    pegs_pagados = [p for p in pegs_pagados if p]
    _email_svc.notificar_remesa_cerrada(remesa_cerrada, pegs_pagados)
    msg = urllib.parse.quote(f"Remesa cerrada. {n} PEGs marcados como PAGADO.")
    return RedirectResponse(url=f"/remesas/{id_remesa}?msg={msg}&msg_type=success", status_code=303)


# ── GENERAR PDF ────────────────────────────────────────────────────────────────

@router.post("/{id_remesa}/generar-pdf")
def remesas_generar_pdf(
    id_remesa: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return HTMLResponse("Remesa no encontrada", status_code=404)
    pagos = [pegs_service.obtener_peg(pid) for pid in remesa.get("pagos", [])]
    pagos = [p for p in pagos if p]
    try:
        pdf_path = generar_pdf_remesa(remesa, pagos)
    except Exception as exc:
        msg = urllib.parse.quote(f"Error al generar el PDF: {str(exc)[:120]}")
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg={msg}&msg_type=error", status_code=303)
    remesas_service.actualizar_pdf_path(id_remesa, pdf_path)
    historial.registrar_evento("RT", id_remesa, "PDF_GENERADO", usuario["nombre_completo"])
    return RedirectResponse(url=f"/remesas/{id_remesa}?msg=PDF+generado+correctamente&msg_type=success", status_code=303)


# ── DESCARGAR PDF ──────────────────────────────────────────────────────────────

@router.get("/{id_remesa}/descargar-pdf")
def remesas_descargar_pdf(
    id_remesa: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return HTMLResponse("Remesa no encontrada", status_code=404)
    if not remesa.get("pdf_path"):
        return RedirectResponse(url=f"/remesas/{id_remesa}?msg=No+hay+PDF+generado&msg_type=error", status_code=303)
    # Resolver siempre como ruta absoluta para que funcione independientemente del CWD
    pdf_abs = str(_PROJECT_ROOT / remesa["pdf_path"])
    if not os.path.exists(pdf_abs):
        historial.registrar_evento("RT", id_remesa, "PDF_DESCARGADO", usuario["nombre_completo"])
        return HTMLResponse("<p style='font-family:sans-serif;padding:20px;'>PDF no disponible en entorno de desarrollo.</p>", status_code=200)
    historial.registrar_evento("RT", id_remesa, "PDF_DESCARGADO", usuario["nombre_completo"])
    return FileResponse(path=pdf_abs, media_type="application/pdf", filename=os.path.basename(pdf_abs))


# ── RUTAS JSON ─────────────────────────────────────────────────────────────────

@router.get("/abiertas")
def remesas_abiertas(usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))):
    abiertas = remesas_service.listar_remesas(estado="ABIERTA")
    return JSONResponse([{"id_remesa": r["id_remesa"], "codigo_remesa": r["codigo_remesa"], "nombre": r["descripcion"], "fecha_creacion": r["fecha_creacion"], "num_pegs": len(r.get("pagos", []))} for r in abiertas])

@router.get("/pegs-disponibles")
def remesas_pegs_disponibles(usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))):
    return JSONResponse(pegs_service.get_pegs_validados_sin_remesa())


# ── AGREGAR / QUITAR PEG ───────────────────────────────────────────────────────

@router.post("/{id_remesa}/agregar-peg/{id_peg}")
def remesas_agregar_peg(id_remesa: int, id_peg: int, usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return JSONResponse({"ok": False, "error": "Remesa no encontrada"}, status_code=404)
    if remesa["estado"] != "ABIERTA":
        return JSONResponse({"ok": False, "error": "La remesa no está abierta"})
    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        return JSONResponse({"ok": False, "error": "PEG no encontrado"}, status_code=404)
    if peg["id_peg_estado"] != 2:
        return JSONResponse({"ok": False, "error": "El PEG no está en estado Validado"})
    if peg.get("id_remesa") is not None:
        return JSONResponse({"ok": False, "error": "El PEG ya está en una remesa"})
    from app.services.proveedores_service import obtener_proveedor as _get_prov
    _prov = _get_prov(peg.get("id_proveedor"))
    if _prov and not _prov.get("cuenta_cliente"):
        return JSONResponse({
            "ok": False,
            "error": f"No se puede remesar: el proveedor «{_prov['razon_social']}» "
                     "no tiene asignada la cuenta contable de acreedor (grupo 4). "
                     "Asígnala en la ficha del proveedor antes de incluirlo en la remesa."
        })
    pegs_service.asignar_a_remesa(id_peg, id_remesa, usuario["nombre_completo"])
    remesas_service.añadir_pago(id_remesa, id_peg)
    historial.registrar_evento("RT", id_remesa, "PEG_AÑADIDA", usuario["nombre_completo"],
                               f"PEG #{id_peg}")
    return JSONResponse({"ok": True, "mensaje": "PEG añadido correctamente"})

@router.post("/{id_remesa}/quitar-peg/{id_peg}")
def remesas_quitar_peg(id_remesa: int, id_peg: int, usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN"))):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return JSONResponse({"ok": False, "error": "Remesa no encontrada"}, status_code=404)
    if remesa["estado"] != "ABIERTA":
        return JSONResponse({"ok": False, "error": "La remesa no está abierta"})
    peg = pegs_service.get_peg_raw(id_peg)
    if not peg:
        return JSONResponse({"ok": False, "error": "PEG no encontrado"}, status_code=404)
    pegs_service.quitar_de_remesa(id_peg, usuario["nombre_completo"])
    remesas_service.quitar_pago(id_remesa, id_peg)
    historial.registrar_evento("RT", id_remesa, "PEG_QUITADA", usuario["nombre_completo"],
                               f"PEG #{id_peg}")
    return JSONResponse({"ok": True, "mensaje": "PEG eliminado de la remesa"})


# ── EXPORTAR SUENLACE (A3Con) ─────────────────────────────────────────────────

@router.get("/{id_remesa}/suenlace")
def remesa_descargar_suenlace(
    id_remesa: int,
    request: Request,
    empresa: str = "real",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    from app.services.suenlace_service import generar_suenlace_remesa
    from fastapi.responses import Response
    try:
        contenido, nombre = generar_suenlace_remesa(id_remesa, empresa)
        historial.registrar_evento("RT", id_remesa, "A3CON_EXPORTADO", usuario["nombre_completo"])
        return Response(
            content=contenido.encode("latin-1"),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── DETALLE (dinámica, antes del listado) ─────────────────────────────────────

@router.get("/{id_remesa}", response_class=HTMLResponse)
def remesas_detalle(
    request: Request,
    id_remesa: int,
    msg: str | None = None,
    msg_type: str = "success",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = remesas_service.obtener_remesa(id_remesa)
    if not remesa:
        return HTMLResponse("Remesa no encontrada", status_code=404)
    pagos = [pegs_service.obtener_peg(pid) for pid in remesa.get("pagos", [])]
    pagos = [p for p in pagos if p]
    banco = mock_bancos.obtener_banco(remesa.get("id_banco", 0))
    return templates.TemplateResponse(request=request, name="remesas/detalle.html",
        context={"remesa": remesa, "pagos": pagos, "banco": banco, "usuario": usuario,
                 "msg": msg, "msg_type": msg_type,
                 "historial": historial.obtener_historial("RT", id_remesa)})


# ── LISTADO (siempre al final) ─────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def remesas_listado(
    request: Request,
    estado: str | None = None,
    msg: str | None = None,
    msg_type: str = "success",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    items = remesas_service.listar_remesas(estado=estado)
    for item in items:
        pegs = [pegs_service.get_peg_raw(id_peg) for id_peg in item.get("pagos", [])]
        item["importe_total"] = sum((p.get("importe_total") or 0) for p in pegs if p)
    return templates.TemplateResponse(request=request, name="remesas/listado.html",
        context={"items": items, "usuario": usuario, "filtro_estado": estado, "msg": msg, "msg_type": msg_type})
