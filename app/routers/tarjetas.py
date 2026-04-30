import traceback
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote

from app.core.templating import templates
from app.core.auth import get_usuario_actual, require_rol
from app.services import mock_tarjetas, mock_movimientos_tarjeta
from app.services import remesas_directas_service
from app.services import pegs_service, proveedores_service
from app.services import mock_remesas_directas
from app.services import historial_remesas_service as historial
from app.services.parser_tarjeta_csv import parsear_csv_tarjeta
from app.services.parser_tarjeta_excel import parsear_excel_santander, parsear_excel_unicaja

router = APIRouter(prefix="/tarjetas", tags=["Tarjetas"])

ESTADOS = ["PENDIENTE", "COTEJADO", "IGNORADO"]


# ── LISTADO ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def listar_movimientos_tarjeta(
    request: Request,
    id_tarjeta: str | None = None,
    estado: str | None = None,
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    id_tarjeta_int = int(id_tarjeta) if id_tarjeta and id_tarjeta.strip().isdigit() else None
    estado_val     = estado.strip() if estado and estado.strip() else None

    items = mock_movimientos_tarjeta.listar_movimientos(id_tarjeta=id_tarjeta_int, estado=estado_val)
    tarjetas = mock_tarjetas.listar_tarjetas(solo_activas=True)
    tarjeta_map = {t["id_tarjeta"]: t for t in mock_tarjetas.listar_tarjetas()}
    cotejo_map = {c["id_mov_tarjeta"]: c for c in mock_movimientos_tarjeta.listar_cotejos()}

    todas_remesas_rd = remesas_directas_service.listar_remesas()
    remesas_abiertas = [r for r in todas_remesas_rd if r["estado"] == "ABIERTA"]

    return templates.TemplateResponse(request=request, name="tarjetas/listado.html", context={
        "usuario": usuario,
        "items": items,
        "tarjetas": tarjetas,
        "tarjeta_map": tarjeta_map,
        "cotejo_map": cotejo_map,
        "remesas_abiertas": remesas_abiertas,
        "filtro_tarjeta": id_tarjeta_int,
        "filtro_estado": estado_val,
        "estados": ESTADOS,
    })


# ── IMPORTAR ──────────────────────────────────────────────────────────────────

@router.get("/importar", response_class=HTMLResponse)
def formulario_importar(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    return templates.TemplateResponse(request=request, name="tarjetas/importar.html", context={
        "usuario": usuario,
        "tarjetas": mock_tarjetas.listar_tarjetas(solo_activas=True),
    })


@router.post("/importar")
async def procesar_importacion(
    request: Request,
    id_tarjeta: int = Form(...),
    fichero: UploadFile = File(...),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    contenido_bytes = await fichero.read()
    nombre_fichero = (fichero.filename or "").lower()

    try:
        if nombre_fichero.endswith(".xlsx"):
            movimientos_raw = parsear_excel_santander(contenido_bytes, id_tarjeta, usuario["username"])
        elif nombre_fichero.endswith(".xls"):
            movimientos_raw = parsear_excel_unicaja(contenido_bytes, id_tarjeta, usuario["username"])
        else:
            # CSV / TXT
            try:
                contenido = contenido_bytes.decode("utf-8")
            except UnicodeDecodeError:
                contenido = contenido_bytes.decode("latin-1")
            movimientos_raw = parsear_csv_tarjeta(contenido, id_tarjeta, usuario["username"])
    except Exception as e:
        traceback.print_exc()
        return templates.TemplateResponse(request=request, name="tarjetas/importar.html", context={
            "usuario": usuario,
            "tarjetas": mock_tarjetas.listar_tarjetas(solo_activas=True),
            "error": f"Error al parsear el fichero: {e}",
        })

    if not movimientos_raw:
        return templates.TemplateResponse(request=request, name="tarjetas/importar.html", context={
            "usuario": usuario,
            "tarjetas": mock_tarjetas.listar_tarjetas(solo_activas=True),
            "error": "No se encontraron movimientos en el fichero. Comprueba que el formato sea CSV con columnas de fecha e importe.",
        })

    importados = duplicados = 0
    for mov in movimientos_raw:
        if mock_movimientos_tarjeta.existe_referencia(mov["referencia"], id_tarjeta):
            duplicados += 1
            continue
        mock_movimientos_tarjeta.crear_movimiento(mov)
        importados += 1

    msg = f"{importados} movimiento(s) importado(s)"
    if duplicados:
        msg += f", {duplicados} duplicado(s) omitido(s)"

    return RedirectResponse(
        url=f"/tarjetas/?id_tarjeta={id_tarjeta}&msg={quote(msg)}&msg_type=success",
        status_code=303,
    )


# ── COTEJAR INDIVIDUAL ────────────────────────────────────────────────────────

@router.post("/{id_mov}/cotejar")
def guardar_cotejo(
    request: Request,
    id_mov: int,
    descripcion: str = Form(""),
):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    mov = mock_movimientos_tarjeta.obtener_movimiento(id_mov)
    if not mov or mov["estado"] != "PENDIENTE":
        return RedirectResponse(url="/tarjetas/", status_code=302)

    desc = descripcion.strip() or mov.get("concepto", "")
    mock_movimientos_tarjeta.crear_cotejo({
        "id_mov_tarjeta": id_mov,
        "tipo_referencia": "MANUAL",
        "id_referencia": None,
        "descripcion": desc,
        "id_usuario": usuario["username"],
    })
    mock_movimientos_tarjeta.marcar_cotejado(id_mov)

    return RedirectResponse(
        url="/tarjetas/?msg=Movimiento+cotejado+correctamente&msg_type=success",
        status_code=303,
    )


# ── IGNORAR ───────────────────────────────────────────────────────────────────

@router.post("/{id_mov}/ignorar")
def ignorar_movimiento(request: Request, id_mov: int):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])
    mock_movimientos_tarjeta.marcar_ignorado(id_mov)
    return RedirectResponse(url="/tarjetas/?msg=Movimiento+marcado+como+ignorado&msg_type=success", status_code=303)


# ── ACCIÓN MASIVA ─────────────────────────────────────────────────────────────

@router.post("/accion-masiva")
async def accion_masiva(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    form = await request.form()
    accion = form.get("accion", "")
    ids_raw = form.getlist("ids")
    ids = [int(i) for i in ids_raw if i.isdigit()]

    if not ids:
        return RedirectResponse(url="/tarjetas/?msg=No+seleccionaste+ningún+movimiento&msg_type=error", status_code=303)

    if accion == "ignorar":
        for id_mov in ids:
            mock_movimientos_tarjeta.marcar_ignorado(id_mov)
        msg = f"{len(ids)} movimiento(s) marcado(s) como ignorado(s)"
    else:
        msg = "Acción no reconocida"

    return RedirectResponse(url=f"/tarjetas/?msg={quote(msg)}&msg_type=success", status_code=303)


# ── AÑADIR A REMESA DIRECTA ───────────────────────────────────────────────────

@router.get("/anadir-a-remesa", response_class=HTMLResponse)
def formulario_anadir_a_remesa(request: Request, ids: str = "", id_remesa: int = 0):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    movimientos_sel = [
        mock_movimientos_tarjeta.obtener_movimiento(i)
        for i in id_list
        if mock_movimientos_tarjeta.obtener_movimiento(i)
        and mock_movimientos_tarjeta.obtener_movimiento(i)["estado"] == "PENDIENTE"
    ]

    if not movimientos_sel:
        return RedirectResponse(url="/tarjetas/?msg=No+hay+movimientos+pendientes+seleccionados&msg_type=error", status_code=302)

    remesa = remesas_directas_service.obtener_remesa(id_remesa) if id_remesa else None
    if not remesa or remesa["estado"] != "ABIERTA":
        return RedirectResponse(url="/tarjetas/?msg=Remesa+no+válida+o+no+abierta&msg_type=error", status_code=302)

    tarjeta_map = {t["id_tarjeta"]: t for t in mock_tarjetas.listar_tarjetas()}
    return templates.TemplateResponse(request=request, name="tarjetas/anadir_a_remesa.html", context={
        "usuario": usuario,
        "movimientos": movimientos_sel,
        "tarjeta_map": tarjeta_map,
        "remesa": remesa,
        "tipos_gasto": mock_remesas_directas.TIPOS_GASTO,
        "ids_str": ids,
        "cuentas_gasto": pegs_service.listar_cuentas_gasto(),
        "servicios_proyectos": pegs_service.get_servicios_proyectos_todos(),
        "proveedores": proveedores_service.listar_proveedores(),
    })


@router.post("/anadir-a-remesa")
async def guardar_anadir_a_remesa(request: Request):
    usuario = get_usuario_actual(request)
    require_rol(usuario, ["ADMIN", "GESTOR_ECONOMICO"])

    form = await request.form()
    id_remesa_str = str(form.get("id_remesa_directa", "")).strip()
    ids_raw = str(form.get("ids_movimientos", ""))
    id_list = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]

    if not id_remesa_str.isdigit():
        return RedirectResponse(url="/tarjetas/?msg=Remesa+no+válida&msg_type=error", status_code=302)
    id_remesa = int(id_remesa_str)

    tipos_gasto_list  = form.getlist("tipo_gasto")
    cuentas_gasto_mov = form.getlist("cuenta_gasto_mov")
    proveedores_mov   = form.getlist("id_proveedor")
    serv_proy_list    = form.getlist("servicio_proyecto")
    descripciones_l   = form.getlist("descripcion_linea")
    porcentajes_raw   = form.getlist("porcentaje_linea")

    n_movs   = len(id_list)
    n_lineas = len(porcentajes_raw)
    lineas_por_mov = (n_lineas // n_movs) if (n_movs > 0 and n_lineas > 0 and n_lineas % n_movs == 0) else max(1, n_lineas)

    movimientos_validos = []
    for idx, id_mov in enumerate(id_list):
        mov = mock_movimientos_tarjeta.obtener_movimiento(id_mov)
        if not mov or mov["estado"] != "PENDIENTE":
            continue

        tipo_gasto   = tipos_gasto_list[idx]  if idx < len(tipos_gasto_list)  else "OTROS"
        cuenta_gasto = cuentas_gasto_mov[idx] if idx < len(cuentas_gasto_mov) else ""
        id_prov      = proveedores_mov[idx]   if idx < len(proveedores_mov)   else ""

        inicio = idx * lineas_por_mov if (n_movs > 0 and n_lineas % n_movs == 0) else 0
        fin    = inicio + lineas_por_mov
        lineas = []
        for j in range(inicio, min(fin, len(porcentajes_raw))):
            try:
                pct = round(float(porcentajes_raw[j].replace(",", ".")), 2)
            except (ValueError, AttributeError):
                pct = 0.0
            if pct <= 0:
                continue
            lineas.append({
                "servicio_proyecto": serv_proy_list[j] if j < len(serv_proy_list) else "",
                "descripcion_linea": descripciones_l[j] if j < len(descripciones_l) else "",
                "porcentaje": pct,
            })

        # Adaptar mov para crear_gasto_desde_movimiento (espera id_movimiento)
        mov_normalizado = {**mov, "id_movimiento": mov["id_mov_tarjeta"]}
        res = remesas_directas_service.crear_gasto_desde_movimiento(
            id_remesa=id_remesa,
            mov=mov_normalizado,
            tipo_gasto=tipo_gasto,
            cuenta_gasto=cuenta_gasto,
            proveedor_id=id_prov,
            lineas_analitica=lineas,
        )
        if res.get("ok"):
            mock_movimientos_tarjeta.crear_cotejo({
                "id_mov_tarjeta": id_mov,
                "tipo_referencia": "REMESA_DIRECTA",
                "id_referencia": id_remesa,
                "descripcion": f"Añadido a remesa directa #{id_remesa}",
                "id_usuario": usuario["username"],
            })
            mock_movimientos_tarjeta.marcar_cotejado(id_mov)
            concepto = (mov.get("concepto") or "")[:50]
            historial.registrar_evento(
                "RD", id_remesa, "GASTO_AÑADIDO", usuario["nombre_completo"],
                f"Tarjeta {mov['fecha_operacion']} · {concepto}",
            )
            movimientos_validos.append(mov)

    if not movimientos_validos:
        return RedirectResponse(url="/tarjetas/?msg=No+se+añadió+ningún+movimiento&msg_type=error", status_code=302)

    n = len(movimientos_validos)
    return RedirectResponse(
        url=f"/tarjetas/?msg={quote(f'{n} movimiento(s) de tarjeta añadido(s) a la remesa directa #{id_remesa}')}&msg_type=success",
        status_code=303,
    )
