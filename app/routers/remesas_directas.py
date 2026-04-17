from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.auth import require_rol
from app.core.templating import templates
from app.services.remesas_directas_service import (
    listar_remesas,
    obtener_remesa,
    obtener_gastos_remesa,
    obtener_gastos_disponibles,
    crear_remesa,
    añadir_gasto,
    quitar_gasto,
    cerrar_remesa,
    totales_remesa,
)
from app.services.pegs_service import _servicios

router = APIRouter(prefix="/remesas-directas", tags=["Remesas Directas"])


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def remesas_directas_listado(
    request: Request,
    tipo: str = "",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    items = listar_remesas(tipo=tipo or None)
    for r in items:
        t = totales_remesa(r["id_remesa_directa"])
        r.update(t)
    return templates.TemplateResponse(
        request=request,
        name="remesas_directas/listado.html",
        context={"usuario": usuario, "items": items, "filtro_tipo": tipo},
    )


# ──────────────────────────────────────────────────────────────────────────────
# NUEVA REMESA
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nueva", response_class=HTMLResponse)
def remesas_directas_nueva(
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    return templates.TemplateResponse(
        request=request,
        name="remesas_directas/nueva.html",
        context={"usuario": usuario, "servicios": _servicios},
    )


@router.post("/nueva")
def remesas_directas_nueva_post(
    tipo: str = Form(...),
    periodo: str = Form(...),
    cuenta_bancaria_id: int = Form(1),
    servicio_id: int = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    datos = {
        "tipo": tipo,
        "periodo": periodo,
        "cuenta_bancaria_id": cuenta_bancaria_id,
        "servicio_id": servicio_id,
    }
    remesa = crear_remesa(datos)
    return RedirectResponse(url=f"/remesas-directas/{remesa['id_remesa_directa']}", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_remesa}", response_class=HTMLResponse)
def remesas_directas_detalle(
    id_remesa: int,
    request: Request,
    msg: str = "",
    msg_type: str = "success",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    remesa = obtener_remesa(id_remesa)
    if not remesa:
        return HTMLResponse("Remesa no encontrada", status_code=404)

    gastos_asignados   = obtener_gastos_remesa(id_remesa)
    gastos_disponibles = obtener_gastos_disponibles(remesa["tipo"]) if remesa["estado"] == "ABIERTA" else []
    totales = totales_remesa(id_remesa)

    return templates.TemplateResponse(
        request=request,
        name="remesas_directas/detalle.html",
        context={
            "usuario": usuario,
            "remesa": remesa,
            "gastos_asignados": gastos_asignados,
            "gastos_disponibles": gastos_disponibles,
            "totales": totales,
            "msg": msg,
            "msg_type": msg_type,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# OPERACIONES
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_remesa}/añadir-gasto")
def remesas_directas_añadir(
    id_remesa: int,
    id_gasto: int = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    resultado = añadir_gasto(id_remesa, id_gasto)
    if resultado["ok"]:
        return RedirectResponse(
            url=f"/remesas-directas/{id_remesa}?msg=Gasto+añadido&msg_type=success",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/remesas-directas/{id_remesa}?msg={resultado['error']}&msg_type=error",
        status_code=303,
    )


@router.post("/{id_remesa}/quitar-gasto")
def remesas_directas_quitar(
    id_remesa: int,
    id_gasto: int = Form(...),
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    resultado = quitar_gasto(id_remesa, id_gasto)
    if resultado["ok"]:
        return RedirectResponse(
            url=f"/remesas-directas/{id_remesa}?msg=Gasto+eliminado+de+la+remesa&msg_type=success",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/remesas-directas/{id_remesa}?msg={resultado['error']}&msg_type=error",
        status_code=303,
    )


@router.post("/{id_remesa}/cerrar")
def remesas_directas_cerrar(
    id_remesa: int,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    resultado = cerrar_remesa(id_remesa)
    if resultado["ok"]:
        return RedirectResponse(
            url=f"/remesas-directas/{id_remesa}?msg=Remesa+cerrada+correctamente&msg_type=success",
            status_code=303,
        )
    return RedirectResponse(
        url=f"/remesas-directas/{id_remesa}?msg={resultado['error']}&msg_type=error",
        status_code=303,
    )


# ──────────────────────────────────────────────────────────────────────────────
# EXPORTAR SUENLACE
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_remesa}/exportar-suenlace")
def remesas_directas_exportar(
    id_remesa: int,
    empresa: str = "real",
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    from app.services.suenlace_service import generar_suenlace_remesa_directa
    try:
        contenido, nombre_fichero = generar_suenlace_remesa_directa(id_remesa, empresa=empresa)
    except ValueError as e:
        return HTMLResponse(f"<p>Error: {e}</p>", status_code=400)

    return Response(
        content=contenido.encode("latin-1", errors="replace"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )
