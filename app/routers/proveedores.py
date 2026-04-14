from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional as _Opt

from app.core.auth import require_login, require_rol
from app.core.templating import templates
from app.services.proveedores_service import (
    listar_proveedores,
    get_proveedores_por_servicio,
    obtener_proveedor,
    crear_proveedor,
    actualizar_iban,
    actualizar_proveedor,
)
from fastapi import HTTPException
from app.services.pegs_service import obtener_servicios, obtener_datos_formulario, listar_pegs_todos, get_parametro
from app.schemas.proveedores import ProveedorCrear

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


# ──────────────────────────────────────────────────────────────────────────────
# LISTADO — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def proveedores_listado(
    request: Request,
    filtro_servicio: str = "todos",
    usuario: dict = Depends(require_login),
):
    if filtro_servicio == "todos":
        items = listar_proveedores()
    elif filtro_servicio == "mio" and usuario.get("id_servicio"):
        items = get_proveedores_por_servicio(usuario["id_servicio"])
    else:
        try:
            items = get_proveedores_por_servicio(int(filtro_servicio))
        except (ValueError, TypeError):
            items = listar_proveedores()

    todos_pegs = listar_pegs_todos()
    for item in items:
        pid = item["id_proveedor"]
        pegs_prov = [p for p in todos_pegs if p["id_proveedor"] == pid]
        item["num_pegs_total"]   = len(pegs_prov)
        item["num_pegs_pagados"] = sum(1 for p in pegs_prov if p["id_peg_estado"] == 4)

    return templates.TemplateResponse(
        request=request,
        name="proveedores/listado.html",
        context={
            "items": items,
            "usuario": usuario,
            "filtro_servicio": filtro_servicio,
            "servicios": obtener_servicios(),
            "formas_pago": obtener_datos_formulario()["formas_pago"],
            "cuenta_saco": get_parametro("cuenta_saco"),
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# ALTA RÁPIDA (JSON) — llamada fetch desde formulario de PEG — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

class _ProveedorRapidoBody(BaseModel):
    razon_social: str
    cif_nif: str
    tipo_persona: _Opt[str] = "JURIDICA"
    nombre_comercial: _Opt[str] = None
    iban: _Opt[str] = None
    id_forma_pago_habitual: _Opt[int] = None
    telefono: _Opt[str] = None
    email: _Opt[str] = None
    direccion: _Opt[str] = None
    localidad: _Opt[str] = None
    codigo_postal: _Opt[str] = None
    provincia: _Opt[str] = None
    cuenta_cliente: _Opt[str] = None


@router.post("/rapido")
def proveedor_rapido(
    body: _ProveedorRapidoBody,
    usuario: dict = Depends(require_login),
):
    data = ProveedorCrear(
        tipo_persona=body.tipo_persona or "JURIDICA",
        cif_nif=body.cif_nif.strip().upper(),
        razon_social=body.razon_social.strip(),
        nombre_comercial=body.nombre_comercial.strip() if body.nombre_comercial else None,
        email=body.email or None,
        telefono=body.telefono or None,
        iban=body.iban.strip().upper().replace(" ", "") if body.iban else None,
        direccion=body.direccion or None,
        localidad=body.localidad or None,
        codigo_postal=body.codigo_postal or None,
        provincia=body.provincia or None,
        cuenta_cliente=body.cuenta_cliente.strip() if body.cuenta_cliente else None,
    )
    nuevo = crear_proveedor(data)
    return JSONResponse({
        "ok": True,
        "id":           nuevo["id_proveedor"],
        "razon_social": nuevo["razon_social"],
        "cif_nif":      nuevo["cif_nif"],
    })


# ──────────────────────────────────────────────────────────────────────────────
# NUEVO PROVEEDOR — solo GESTOR / SUPERADMIN
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/nuevo", response_class=HTMLResponse)
def proveedores_nuevo(
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")),
):
    return templates.TemplateResponse(
        request=request,
        name="proveedores/nuevo.html",
        context={
            "usuario": usuario,
            "cuenta_saco": get_parametro("cuenta_saco"),
        },
    )


@router.post("/nuevo")
def proveedores_nuevo_post(
    usuario: dict = Depends(require_rol("GESTOR_SERVICIO", "GESTOR_ECONOMICO", "ADMIN")),
    tipo_persona: str = Form(...),
    cif_nif: str = Form(...),
    razon_social: str = Form(...),
    nombre_comercial: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    iban: str = Form(""),
    direccion: str = Form(""),
    localidad: str = Form(""),
    codigo_postal: str = Form(""),
    provincia: str = Form(""),
    cuenta_cliente: str = Form(""),
):
    data = ProveedorCrear(
        tipo_persona=tipo_persona,
        cif_nif=cif_nif,
        razon_social=razon_social,
        nombre_comercial=nombre_comercial or None,
        email=email or None,
        telefono=telefono or None,
        iban=iban or None,
        direccion=direccion or None,
        localidad=localidad or None,
        codigo_postal=codigo_postal or None,
        provincia=provincia or None,
        cuenta_cliente=cuenta_cliente.strip() or None,
    )
    crear_proveedor(data)
    return RedirectResponse(url="/proveedores/", status_code=303)


# ──────────────────────────────────────────────────────────────────────────────
# SIGUIENTE CUENTA CLIENTE — GESTOR_ECONOMICO y ADMIN
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/siguiente-cuenta-cliente")
def get_siguiente_cuenta_cliente(
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    from fastapi.responses import JSONResponse
    from app import mock_data
    return JSONResponse(content={
        "cuenta": mock_data.siguiente_cuenta_cliente()
    })


# ──────────────────────────────────────────────────────────────────────────────
# DATOS JSON Y EDICIÓN JSON — GESTOR_ECONOMICO y ADMIN
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_proveedor}/datos-json")
def proveedor_datos_json(
    id_proveedor: int,
    request: Request,
    usuario: dict = Depends(require_login),
):
    p = obtener_proveedor(id_proveedor)
    if not p:
        raise HTTPException(status_code=404, detail="No encontrado")
    return JSONResponse(content={
        "id_proveedor":   p["id_proveedor"],
        "razon_social":   p.get("razon_social", ""),
        "nif":            p.get("cif_nif", ""),
        "iban":           p.get("iban", ""),
        "email":          p.get("email", ""),
        "telefono":       p.get("telefono", ""),
        "cuenta_cliente": p.get("cuenta_cliente", ""),
    })


@router.post("/{id_proveedor}/editar-json")
async def proveedor_editar_json(
    id_proveedor: int,
    request: Request,
    usuario: dict = Depends(require_rol("GESTOR_ECONOMICO", "ADMIN")),
):
    datos = await request.json()
    p = obtener_proveedor(id_proveedor)
    if not p:
        raise HTTPException(status_code=404, detail="No encontrado")
    # Mapear nif → cif_nif (nombre real del campo)
    mapeo = {"razon_social": "razon_social", "nif": "cif_nif",
             "iban": "iban", "email": "email", "telefono": "telefono",
             "cuenta_cliente": "cuenta_cliente"}
    for campo_entrada, campo_real in mapeo.items():
        if campo_entrada in datos:
            p[campo_real] = datos[campo_entrada]
    return JSONResponse(content={"ok": True})


# ──────────────────────────────────────────────────────────────────────────────
# EDITAR PROVEEDOR COMPLETO — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_proveedor}/editar")
def proveedor_editar(
    id_proveedor: int,
    tipo_persona: str = Form(...),
    cif_nif: str = Form(...),
    razon_social: str = Form(...),
    nombre_comercial: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    iban: str = Form(""),
    direccion: str = Form(""),
    localidad: str = Form(""),
    codigo_postal: str = Form(""),
    provincia: str = Form(""),
    usuario: dict = Depends(require_login),
):
    datos = {
        "tipo_persona": tipo_persona,
        "cif_nif": cif_nif.strip().upper(),
        "razon_social": razon_social.strip(),
        "nombre_comercial": nombre_comercial.strip() or None,
        "email": email.strip() or None,
        "telefono": telefono.strip() or None,
        "iban": iban.strip().upper().replace(" ", "") or None,
        "direccion": direccion.strip() or None,
        "localidad": localidad.strip() or None,
        "codigo_postal": codigo_postal.strip() or None,
        "provincia": provincia.strip() or None,
    }
    ok = actualizar_proveedor(id_proveedor, datos)
    if not ok:
        return JSONResponse({"error": "Proveedor no encontrado"}, status_code=404)
    proveedor = obtener_proveedor(id_proveedor)
    return JSONResponse({"ok": True, **proveedor})


# ──────────────────────────────────────────────────────────────────────────────
# EDITAR IBAN inline — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{id_proveedor}/iban")
def proveedor_actualizar_iban(
    id_proveedor: int,
    iban: str = Form(""),
    usuario: dict = Depends(require_login),
):
    ok = actualizar_iban(id_proveedor, iban.strip() or None)
    if not ok:
        return JSONResponse({"error": "Proveedor no encontrado"}, status_code=404)
    return JSONResponse({"ok": True, "iban": iban.strip() or None})


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE JSON — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_proveedor}/json")
def proveedor_detalle_json(
    id_proveedor: int,
    usuario: dict = Depends(require_login),
):
    item = obtener_proveedor(id_proveedor)
    if not item:
        return JSONResponse({"error": "Proveedor no encontrado"}, status_code=404)
    todos_pegs = listar_pegs_todos()
    pegs_prov = [p for p in todos_pegs if p["id_proveedor"] == id_proveedor]
    result = dict(item)
    result["pegs"] = pegs_prov
    return JSONResponse(result)


# ──────────────────────────────────────────────────────────────────────────────
# DETALLE HTML — todos los roles
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{id_proveedor}", response_class=HTMLResponse)
def proveedor_detalle(
    request: Request,
    id_proveedor: int,
    usuario: dict = Depends(require_login),
):
    item = obtener_proveedor(id_proveedor)
    if not item:
        return HTMLResponse("Proveedor no encontrado", status_code=404)

    html = f"""
    <html>
        <head><title>Proveedor {item['razon_social']}</title></head>
        <body style="font-family: Arial; padding: 24px;">
            <h1>{item['razon_social']}</h1>
            <p><strong>CIF/NIF:</strong> {item['cif_nif']}</p>
            <p><strong>Tipo:</strong> {item['tipo_persona']}</p>
            <p><strong>Email:</strong> {item.get('email') or ''}</p>
            <p><strong>Teléfono:</strong> {item.get('telefono') or ''}</p>
            <p><strong>IBAN:</strong> {item.get('iban') or ''}</p>
            <p><a href="/proveedores/">Volver al listado</a></p>
        </body>
    </html>
    """
    return HTMLResponse(html)
