import traceback
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote

from app.core.templating import templates
from app.core.auth import get_usuario_actual, require_rol
from app.services import mock_bancos, mock_movimientos, mock_cotejos
from app.services import remesas_service
from app.services import mock_remesas_directas
from app.services.parser_extracto import detectar_y_parsear
from app.services import pegs_service
from app.services import proveedores_service

router = APIRouter(prefix="/movimientos", tags=["Movimientos bancarios"])

ESTADOS = ["PENDIENTE", "COTEJADO", "IGNORADO"]
TIPOS = ["TRANSFERENCIA", "DOMICILIACION", "TARJETA", "COMISION", "OTROS"]


# ── LISTADO ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def listar_movimientos(
    request: Request,
    id_banco: int | None = None,
    estado: str | None = None,
    tipo: str | None = None,
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    items = mock_movimientos.listar_movimientos(id_banco=id_banco, estado=estado, tipo=tipo)
    bancos = mock_bancos.listar_bancos(solo_activas=True)
    banco_map = {b["id_banco"]: b for b in mock_bancos.listar_bancos()}
    cotejo_map = {c["id_movimiento"]: c for c in mock_cotejos.listar_cotejos()}

    return templates.TemplateResponse(request=request, name="movimientos/listado.html", context={
        "usuario": usuario,
        "items": items,
        "bancos": bancos,
        "banco_map": banco_map,
        "cotejo_map": cotejo_map,
        "filtro_banco": id_banco,
        "filtro_estado": estado,
        "filtro_tipo": tipo,
        "estados": ESTADOS,
        "tipos": TIPOS,
    })


# ── IMPORTAR ──────────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
def formulario_importar(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    bancos = mock_bancos.listar_bancos(solo_activas=True)
    return templates.TemplateResponse(request=request, name="movimientos/importar.html", context={
        "usuario": usuario,
        "bancos": bancos,
    })


@router.post("/importar")
async def procesar_importacion(
    request: Request,
    id_banco: int = Form(...),
    fichero: UploadFile = File(...),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    contenido_bytes = await fichero.read()
    try:
        contenido = contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        contenido = contenido_bytes.decode("latin-1")

    nombre = fichero.filename or ""

    try:
        movimientos_raw = detectar_y_parsear(contenido, nombre, id_banco, usuario["username"], contenido_bytes=contenido_bytes)
    except Exception as e:
        traceback.print_exc()
        bancos = mock_bancos.listar_bancos(solo_activas=True)
        return templates.TemplateResponse(request=request, name="movimientos/importar.html", context={
            "usuario": usuario,
            "bancos": bancos,
            "error": f"Error al parsear el fichero: {e}",
        })

    if not movimientos_raw:
        bancos = mock_bancos.listar_bancos(solo_activas=True)
        return templates.TemplateResponse(request=request, name="movimientos/importar.html", context={
            "usuario": usuario,
            "bancos": bancos,
            "error": "No se encontraron movimientos en el fichero. Comprueba que el formato sea AEB Norma 43 o CSV con cabeceras correctas.",
        })

    importados = 0
    duplicados = 0
    for mov in movimientos_raw:
        if mock_movimientos.existe_referencia(mov["referencia_banco"], id_banco):
            duplicados += 1
            continue
        mock_movimientos.crear_movimiento(mov)
        importados += 1

    msg = f"{importados} movimiento(s) importado(s)"
    if duplicados:
        msg += f", {duplicados} duplicado(s) omitido(s)"

    return RedirectResponse(
        url=f"/movimientos/?id_banco={id_banco}&msg={quote(msg)}&msg_type=success",
        status_code=303,
    )


# ── COTEJO INDIVIDUAL ─────────────────────────────────────────────────────────

@router.get("/{id_movimiento}/cotejar", response_class=HTMLResponse)
def formulario_cotejar(request: Request, id_movimiento: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    mov = mock_movimientos.obtener_movimiento(id_movimiento)
    if not mov or mov["estado"] != "PENDIENTE":
        return RedirectResponse(url="/movimientos/", status_code=302)

    banco = mock_bancos.obtener_banco(mov["id_banco"])
    remesas = remesas_service.listar_remesas()
    importe_abs = abs(mov["importe"])

    # Ordenar remesas por proximidad de importe (mejor coincidencia primero)
    from app.services.pegs_service import obtener_peg
    def _total_remesa(r):
        pegs = [obtener_peg(pid) for pid in r.get("pagos", [])]
        return sum(p.get("importe_total", 0) for p in pegs if p)

    remesas_con_total = []
    for r in remesas:
        total = _total_remesa(r)
        diff_pct = abs(total - importe_abs) / importe_abs if importe_abs else 1
        remesas_con_total.append({**r, "_total": total, "_match_pct": diff_pct})
    remesas_con_total.sort(key=lambda r: r["_match_pct"])

    return templates.TemplateResponse(request=request, name="movimientos/cotejar.html", context={
        "usuario": usuario,
        "mov": mov,
        "banco": banco,
        "remesas": remesas_con_total,
    })


@router.post("/{id_movimiento}/cotejar")
def guardar_cotejo(
    request: Request,
    id_movimiento: int,
    tipo_referencia: str = Form(...),
    id_referencia: int | None = Form(None),
    descripcion: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    mov = mock_movimientos.obtener_movimiento(id_movimiento)
    if not mov:
        return RedirectResponse(url="/movimientos/", status_code=302)

    desc = descripcion.strip()
    if tipo_referencia == "REMESA" and id_referencia:
        remesa = remesas_service.obtener_remesa(id_referencia)
        desc = desc or (remesa["codigo_remesa"] if remesa else "")

    mock_cotejos.crear_cotejo({
        "id_movimiento": id_movimiento,
        "tipo_referencia": tipo_referencia,
        "id_referencia": id_referencia,
        "descripcion": desc,
        "id_usuario": usuario["username"],
    })
    mock_movimientos.marcar_cotejado(id_movimiento)

    return RedirectResponse(
        url="/movimientos/?msg=Movimiento+cotejado+correctamente&msg_type=success",
        status_code=303,
    )


# ── ACCIONES MASIVAS ──────────────────────────────────────────────────────────

@router.post("/accion-masiva")
async def accion_masiva(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    form = await request.form()
    accion = form.get("accion", "")
    ids_raw = form.getlist("ids")
    ids = [int(i) for i in ids_raw if i.isdigit()]

    if not ids:
        return RedirectResponse(url="/movimientos/?msg=No+seleccionaste+ningún+movimiento&msg_type=error", status_code=303)

    if accion == "ignorar":
        for id_mov in ids:
            mock_movimientos.marcar_ignorado(id_mov)
        msg = f"{len(ids)} movimiento(s) marcado(s) como ignorado(s)"

    elif accion == "agrupar":
        descripcion = str(form.get("descripcion_grupo", "")).strip() or "Agrupación manual"
        for id_mov in ids:
            mov = mock_movimientos.obtener_movimiento(id_mov)
            if mov and mov["estado"] == "PENDIENTE":
                mock_cotejos.crear_cotejo({
                    "id_movimiento": id_mov,
                    "tipo_referencia": "MANUAL",
                    "id_referencia": None,
                    "descripcion": descripcion,
                    "id_usuario": usuario["username"],
                })
                mock_movimientos.marcar_cotejado(id_mov)
        msg = f"{len(ids)} movimiento(s) agrupado(s) como: {descripcion}"

    else:
        msg = "Acción no reconocida"

    from urllib.parse import quote
    return RedirectResponse(url=f"/movimientos/?msg={quote(msg)}&msg_type=success", status_code=303)


# ── AUTO-COTEJO ───────────────────────────────────────────────────────────────

@router.post("/autocotejar")
def autocotejar(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    pendientes = mock_movimientos.listar_movimientos(estado="PENDIENTE")
    remesas = remesas_service.listar_remesas()
    n = mock_cotejos.autocotejar_pendientes(pendientes, remesas)

    msg = f"{n} movimiento(s) cotejado(s) automáticamente" if n else "No se encontraron coincidencias automáticas"
    from urllib.parse import quote
    return RedirectResponse(url=f"/movimientos/?msg={quote(msg)}&msg_type=success", status_code=303)


# ── LISTADO REMESAS BANCARIAS ─────────────────────────────────────────────────

@router.get("/remesas-bancarias", response_class=HTMLResponse)
def listar_remesas_bancarias(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    items = mock_remesas_directas.listar_remesas_directas()
    banco_map = {b["id_banco"]: b for b in mock_bancos.listar_bancos()}

    return templates.TemplateResponse(request=request, name="movimientos/remesas_bancarias.html", context={
        "usuario": usuario,
        "items": items,
        "banco_map": banco_map,
    })


@router.get("/remesas-bancarias/{id_rd}", response_class=HTMLResponse)
def detalle_remesa_bancaria(request: Request, id_rd: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    rd = mock_remesas_directas.obtener_remesa_directa(id_rd)
    if not rd:
        return RedirectResponse(url="/movimientos/remesas-bancarias", status_code=302)

    banco = mock_bancos.obtener_banco(rd["id_banco"])
    mov = mock_movimientos.obtener_movimiento(rd["id_movimiento"])

    return templates.TemplateResponse(request=request, name="movimientos/remesa_bancaria_detalle.html", context={
        "usuario": usuario,
        "rd": rd,
        "banco": banco,
        "mov": mov,
    })


@router.get("/remesas-bancarias/{id_rd}/pdf")
def remesa_bancaria_pdf(request: Request, id_rd: int):
    from fastapi.responses import FileResponse
    from app.services.pdf_remesa_service import generar_pdf_remesa_bancaria
    import os

    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    rd = mock_remesas_directas.obtener_remesa_directa(id_rd)
    if not rd:
        return HTMLResponse("Remesa no encontrada", status_code=404)

    banco = mock_bancos.obtener_banco(rd["id_banco"])
    mov   = mock_movimientos.obtener_movimiento(rd["id_movimiento"])

    ruta_relativa = generar_pdf_remesa_bancaria(rd, banco, mov)
    ruta_absoluta = os.path.join(
        os.path.dirname(__file__), "..", "..", ruta_relativa
    )
    ruta_absoluta = os.path.normpath(ruta_absoluta)

    nombre = os.path.basename(ruta_absoluta)
    return FileResponse(
        path=ruta_absoluta,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/remesas-bancarias/{id_rd}/exportar-suenlace")
def remesa_bancaria_suenlace(request: Request, id_rd: int, empresa: str = "real"):
    from fastapi.responses import Response
    from app.services.suenlace_service import generar_suenlace_remesa_bancaria

    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    try:
        contenido, nombre_fichero = generar_suenlace_remesa_bancaria(id_rd, empresa=empresa)
    except ValueError as e:
        return HTMLResponse(f"<p>Error: {e}</p>", status_code=400)

    return Response(
        content=contenido.encode("latin-1", errors="replace"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


# ── REMESA DIRECTA GRUPAL (varios movimientos → una remesa) ──────────────────

@router.get("/remesa-directa-grupal", response_class=HTMLResponse)
def formulario_remesa_directa_grupal(request: Request, ids: str = ""):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    movimientos_sel = [
        mock_movimientos.obtener_movimiento(i)
        for i in id_list
        if mock_movimientos.obtener_movimiento(i) and mock_movimientos.obtener_movimiento(i)["estado"] == "PENDIENTE"
    ]

    if not movimientos_sel:
        return RedirectResponse(url="/movimientos/?msg=No+hay+movimientos+pendientes+seleccionados&msg_type=error", status_code=302)

    banco_map = {b["id_banco"]: b for b in mock_bancos.listar_bancos()}
    return templates.TemplateResponse(request=request, name="movimientos/remesa_directa_grupal.html", context={
        "usuario": usuario,
        "movimientos": movimientos_sel,
        "banco_map": banco_map,
        "tipos_gasto": mock_remesas_directas.TIPOS_GASTO,
        "ids_str": ids,
        "cuentas_gasto": pegs_service.listar_cuentas_gasto(),
        "servicios_proyectos": pegs_service.get_servicios_proyectos_todos(),
        "proveedores": proveedores_service.listar_proveedores(),
    })


@router.post("/remesa-directa-grupal")
async def guardar_remesa_directa_grupal(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    form = await request.form()
    descripcion       = str(form.get("descripcion", "")).strip()
    ids_raw           = str(form.get("ids_movimientos", ""))
    id_list           = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]

    # Un valor por movimiento
    tipos_gasto_list   = form.getlist("tipo_gasto")
    cuentas_gasto_mov  = form.getlist("cuenta_gasto_mov")
    proveedores_mov    = form.getlist("id_proveedor")

    # Múltiples por línea analítica (concatenados en orden)
    serv_proy_list    = form.getlist("servicio_proyecto")
    descripciones_l   = form.getlist("descripcion_linea")
    porcentajes_raw   = form.getlist("porcentaje_linea")

    # Agrupar líneas por movimiento: distribuimos equitativamente si es múltiplo
    n_movs   = len(id_list)
    n_lineas = len(porcentajes_raw)
    lineas_por_mov = (n_lineas // n_movs) if (n_movs > 0 and n_lineas % n_movs == 0) else max(1, n_lineas)

    lineas_globales  = []
    movimientos_validos = []
    for idx, id_mov in enumerate(id_list):
        mov = mock_movimientos.obtener_movimiento(id_mov)
        if not mov or mov["estado"] != "PENDIENTE":
            continue

        tipo_gasto   = tipos_gasto_list[idx]   if idx < len(tipos_gasto_list)   else "OTROS"
        cuenta_gasto = cuentas_gasto_mov[idx]  if idx < len(cuentas_gasto_mov)  else ""
        id_prov_mov  = proveedores_mov[idx]    if idx < len(proveedores_mov)    else ""
        importe_mov  = abs(mov["importe"])

        inicio = idx * lineas_por_mov if (n_movs > 0 and n_lineas % n_movs == 0) else 0
        fin    = inicio + lineas_por_mov

        for j in range(inicio, min(fin, len(porcentajes_raw))):
            try:
                pct = round(float(porcentajes_raw[j].replace(",", ".")), 2)
            except (ValueError, AttributeError):
                pct = 0.0
            if pct <= 0:
                continue
            lineas_globales.append({
                "tipo_gasto":        tipo_gasto,
                "cuenta_gasto":      cuenta_gasto,
                "servicio_proyecto": serv_proy_list[j]  if j < len(serv_proy_list)  else "",
                "descripcion_linea": descripciones_l[j] if j < len(descripciones_l) else "",
                "porcentaje":        pct,
                "importe":           round(importe_mov * pct / 100, 2),
            })

        movimientos_validos.append(mov)

    if not movimientos_validos:
        return RedirectResponse(url="/movimientos/", status_code=302)

    importe_total = sum(abs(m["importe"]) for m in movimientos_validos)

    # Crear remesa directa grupal
    mock_remesas_directas.crear_remesa_directa({
        "id_movimiento":   movimientos_validos[0]["id_movimiento"],
        "ids_movimientos": [m["id_movimiento"] for m in movimientos_validos],
        "id_banco":        movimientos_validos[0]["id_banco"],
        "descripcion":     descripcion,
        "tipo_gasto":      tipos_gasto_list[0] if tipos_gasto_list else "OTROS",
        "id_proveedor":    proveedores_mov[0] if proveedores_mov else "",
        "importe_total":   importe_total,
        "lineas":          lineas_globales,
        "id_usuario":      usuario["username"],
    })

    # Cotejar todos los movimientos
    for mov in movimientos_validos:
        mock_cotejos.crear_cotejo({
            "id_movimiento":   mov["id_movimiento"],
            "tipo_referencia": "REMESA_DIRECTA",
            "id_referencia":   None,
            "descripcion":     descripcion,
            "id_usuario":      usuario["username"],
        })
        mock_movimientos.marcar_cotejado(mov["id_movimiento"])

    n = len(movimientos_validos)
    return RedirectResponse(
        url=f"/movimientos/?msg={quote(f'Remesa directa creada y {n} movimiento(s) cotejado(s)')}&msg_type=success",
        status_code=303,
    )


# ── REMESA DIRECTA INDIVIDUAL ─────────────────────────────────────────────────

@router.get("/{id_movimiento}/remesa-directa", response_class=HTMLResponse)
def formulario_remesa_directa(request: Request, id_movimiento: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    mov = mock_movimientos.obtener_movimiento(id_movimiento)
    if not mov or mov["estado"] != "PENDIENTE":
        return RedirectResponse(url="/movimientos/", status_code=302)

    banco = mock_bancos.obtener_banco(mov["id_banco"])

    return templates.TemplateResponse(request=request, name="movimientos/remesa_directa.html", context={
        "usuario": usuario,
        "mov": mov,
        "banco": banco,
        "tipos_gasto": mock_remesas_directas.TIPOS_GASTO,
        "cuentas_gasto": pegs_service.listar_cuentas_gasto(),
        "servicios_proyectos": pegs_service.get_servicios_proyectos_todos(),
        "proveedores": proveedores_service.listar_proveedores(),
    })


@router.post("/{id_movimiento}/remesa-directa")
async def guardar_remesa_directa(request: Request, id_movimiento: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    mov = mock_movimientos.obtener_movimiento(id_movimiento)
    if not mov:
        return RedirectResponse(url="/movimientos/", status_code=302)

    form = await request.form()

    descripcion      = str(form.get("descripcion", "")).strip()
    tipo_gasto       = str(form.get("tipo_gasto", "OTROS")).strip()
    cuenta_gasto_mov = str(form.get("cuenta_gasto_mov", "")).strip()
    id_proveedor_raw = str(form.get("id_proveedor", "")).strip()
    serv_proy_list   = form.getlist("servicio_proyecto")
    descripciones_l  = form.getlist("descripcion_linea")
    porcentajes_raw  = form.getlist("porcentaje_linea")

    importe_total = abs(mov["importe"])
    lineas = []
    for sp, desc, pct_raw in zip(serv_proy_list, descripciones_l, porcentajes_raw):
        try:
            pct = round(float(pct_raw.replace(",", ".")), 2)
        except (ValueError, AttributeError):
            pct = 0.0
        if pct > 0:
            lineas.append({
                "tipo_gasto":        tipo_gasto,
                "cuenta_gasto":      cuenta_gasto_mov,
                "servicio_proyecto": sp,
                "descripcion_linea": desc,
                "porcentaje":        pct,
                "importe":           round(importe_total * pct / 100, 2),
            })

    if not lineas or not cuenta_gasto_mov:
        banco = mock_bancos.obtener_banco(mov["id_banco"])
        return templates.TemplateResponse(request=request, name="movimientos/remesa_directa.html", context={
            "usuario": usuario,
            "mov": mov,
            "banco": banco,
            "tipos_gasto": mock_remesas_directas.TIPOS_GASTO,
            "cuentas_gasto": pegs_service.listar_cuentas_gasto(),
            "servicios_proyectos": pegs_service.get_servicios_proyectos_todos(),
            "proveedores": proveedores_service.listar_proveedores(),
            "error": "Selecciona la cuenta de gasto y añade al menos una línea analítica.",
        })

    mock_remesas_directas.crear_remesa_directa({
        "id_movimiento":  id_movimiento,
        "id_banco":       mov["id_banco"],
        "descripcion":    descripcion or mov["concepto"],
        "tipo_gasto":     tipo_gasto,
        "cuenta_gasto":   cuenta_gasto_mov,
        "id_proveedor":   id_proveedor_raw,
        "importe_total":  importe_total,
        "lineas":         lineas,
        "id_usuario":     usuario["username"],
    })

    # Cotejar el movimiento automáticamente
    mock_cotejos.crear_cotejo({
        "id_movimiento":   id_movimiento,
        "tipo_referencia": "REMESA_DIRECTA",
        "id_referencia":   None,
        "descripcion":     descripcion or tipo_gasto,
        "id_usuario":      usuario["username"],
    })
    mock_movimientos.marcar_cotejado(id_movimiento)

    return RedirectResponse(
        url=f"/movimientos/?msg={quote('Remesa directa creada y movimiento cotejado')}&msg_type=success",
        status_code=303,
    )


# ── IGNORAR INDIVIDUAL ────────────────────────────────────────────────────────

@router.post("/{id_movimiento}/ignorar")
def ignorar_movimiento(request: Request, id_movimiento: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    mock_movimientos.marcar_ignorado(id_movimiento)
    return RedirectResponse(url="/movimientos/?msg=Movimiento+marcado+como+ignorado&msg_type=success", status_code=303)
