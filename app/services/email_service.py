"""
Notificaciones por correo electrónico para el ciclo de vida de PEGs y solicitudes.

Plantillas HTML en app/templates/emails/  (Jinja2, extienden _base.html).
Configuración SMTP en .env:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, BASE_URL
"""
from app.core.email import enviar_email
from app.services import mock_usuarios
from app.core.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render(template_name: str, **ctx) -> str:
    from app.core.templating import templates
    ctx.setdefault("base_url", settings.BASE_URL)
    return templates.env.get_template(f"emails/{template_name}").render(**ctx)


def _emails_gestores() -> list[str]:
    return [
        u["email"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] == "GESTOR_ECONOMICO" and u.get("email")
    ]


def _email_usuario(id_usuario: int) -> str | None:
    u = mock_usuarios.obtener_usuario(id_usuario)
    return u.get("email") if u else None


def _emails_gs_de_servicios(ids_servicios: set[int]) -> list[str]:
    return [
        u["email"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] == "GESTOR_SERVICIO"
        and u.get("id_servicio") in ids_servicios
        and u.get("email")
    ]


def _emails_gs_de_remesa(peg_ids: list[int]) -> list[str]:
    from app.services import pegs_service
    ids_servicios = {
        peg["id_servicio"]
        for pid in peg_ids
        if (peg := pegs_service.get_peg_raw(pid)) is not None
    }
    return _emails_gs_de_servicios(ids_servicios)


# ── PEGs ──────────────────────────────────────────────────────────────────────

def enviar_notificacion_nuevo_peg(peg: dict, usuario_creador: dict) -> bool:
    destinatarios = _emails_gestores()
    if not destinatarios:
        return False
    cuerpo = _render(
        "peg_creada.html",
        codigo_peg=peg["codigo_peg"],
        servicio=peg.get("nombre_servicio", ""),
        proveedor=peg.get("nombre_proveedor", ""),
        descripcion=peg["descripcion_gasto"],
        importe=f"{peg['importe_total']:.2f} €",
        creado_por=usuario_creador.get("nombre_completo", usuario_creador.get("username", "")),
        url=f"{settings.BASE_URL}/pegs/{peg['id_peg']}",
    )
    return enviar_email(destinatarios, f"[SGPEG] Nuevo PEG pendiente de validación: {peg['codigo_peg']}", cuerpo)


def notificar_peg_creada(peg: dict, usuario_solicitante: dict) -> None:
    email_sol = usuario_solicitante.get("email")
    if email_sol:
        cuerpo = _render(
            "peg_creada.html",
            codigo_peg=peg["codigo_peg"],
            servicio=peg.get("nombre_servicio", ""),
            proveedor=peg.get("nombre_proveedor", ""),
            descripcion=peg["descripcion_gasto"],
            importe=f"{peg['importe_total']:.2f} €",
            creado_por=usuario_solicitante.get("nombre_completo", ""),
            url=f"{settings.BASE_URL}/pegs/{peg['id_peg']}",
        )
        enviar_email(email_sol, f"[SGPEG] PEG registrada: {peg['codigo_peg']}", cuerpo)
    enviar_notificacion_nuevo_peg(peg, usuario_solicitante)


def notificar_peg_validada(peg: dict, email_solicitante: str) -> None:
    cuerpo = _render(
        "peg_validada.html",
        codigo_peg=peg["codigo_peg"],
        descripcion=peg["descripcion_gasto"],
        importe=f"{peg['importe_total']:.2f} €",
        proveedor=peg.get("nombre_proveedor", ""),
        url=f"{settings.BASE_URL}/pegs/{peg['id_peg']}",
    )
    enviar_email(email_solicitante, f"[SGPEG] PEG validada: {peg['codigo_peg']}", cuerpo)


def notificar_peg_incidencia(
    peg: dict, email_solicitante: str, descripcion_incidencia: str
) -> None:
    cuerpo = _render(
        "peg_incidencia.html",
        codigo_peg=peg["codigo_peg"],
        descripcion=peg["descripcion_gasto"],
        importe=f"{peg['importe_total']:.2f} €",
        comentario=descripcion_incidencia,
        url=f"{settings.BASE_URL}/pegs/{peg['id_peg']}",
    )
    enviar_email(email_solicitante, f"[SGPEG] Incidencia en PEG: {peg['codigo_peg']}", cuerpo)


def notificar_peg_pagada(peg: dict, email_solicitante: str) -> None:
    cuerpo = _render(
        "peg_pagada.html",
        codigo_peg=peg["codigo_peg"],
        descripcion=peg["descripcion_gasto"],
        importe=f"{peg['importe_total']:.2f} €",
        proveedor=peg.get("nombre_proveedor", ""),
        fecha_pago=peg.get("fecha_pago", ""),
        url=f"{settings.BASE_URL}/pegs/{peg['id_peg']}",
    )
    enviar_email(email_solicitante, f"[SGPEG] PEG pagada: {peg['codigo_peg']}", cuerpo)


# ── Solicitudes ───────────────────────────────────────────────────────────────

def notificar_solicitud_creada(solicitud: dict, nombre_solicitante: str) -> None:
    destinatarios = _emails_gestores()
    if not destinatarios:
        return
    id_sol = solicitud["id_solicitud"]
    from datetime import datetime
    fecha_raw = solicitud.get("fecha_creacion")
    fecha = fecha_raw.strftime("%d/%m/%Y %H:%M") if isinstance(fecha_raw, datetime) else str(fecha_raw or "")
    cuerpo = _render(
        "solicitud_creada.html",
        id_solicitud=id_sol,
        concepto=solicitud["concepto"],
        importe=f"{solicitud['importe_estimado']:.2f} €",
        nombre_solicitante=nombre_solicitante,
        fecha=fecha,
        url=f"{settings.BASE_URL}/solicitudes/{id_sol}",
    )
    enviar_email(destinatarios, f"[SGPEG] Nueva solicitud pendiente de autorización: #{id_sol}", cuerpo)


def notificar_solicitud_autorizada(solicitud: dict, email_solicitante: str) -> None:
    id_sol = solicitud["id_solicitud"]
    id_autor = solicitud.get("id_usuario_autorizador")
    autor = mock_usuarios.obtener_usuario(id_autor) if id_autor else None
    cuerpo = _render(
        "solicitud_autorizada.html",
        id_solicitud=id_sol,
        concepto=solicitud["concepto"],
        importe=f"{solicitud['importe_estimado']:.2f} €",
        autorizado_por=autor["nombre_completo"] if autor else "Gestor económico",
        url=f"{settings.BASE_URL}/solicitudes/{id_sol}",
    )
    enviar_email(email_solicitante, f"[SGPEG] Solicitud autorizada: #{id_sol}", cuerpo)


def notificar_solicitud_denegada(
    solicitud: dict, email_solicitante: str, motivo: str
) -> None:
    id_sol = solicitud["id_solicitud"]
    id_autor = solicitud.get("id_usuario_autorizador")
    autor = mock_usuarios.obtener_usuario(id_autor) if id_autor else None
    cuerpo = _render(
        "solicitud_denegada.html",
        id_solicitud=id_sol,
        concepto=solicitud["concepto"],
        importe=f"{solicitud['importe_estimado']:.2f} €",
        denegado_por=autor["nombre_completo"] if autor else "Gestor económico",
        motivo=motivo,
        url=f"{settings.BASE_URL}/solicitudes/{id_sol}",
    )
    enviar_email(email_solicitante, f"[SGPEG] Solicitud denegada: #{id_sol}", cuerpo)


# ── Remesas ───────────────────────────────────────────────────────────────────

def notificar_remesa_generada(remesa: dict, peg_ids: list[int]) -> None:
    destinatarios = _emails_gs_de_remesa(peg_ids)
    if not destinatarios:
        return
    from app.services import pegs_service
    from datetime import datetime
    pegs = [pegs_service.obtener_peg(pid) for pid in peg_ids]
    pegs = [p for p in pegs if p]
    importe_total = sum(p.get("importe_total", 0) for p in pegs)
    codigo = remesa.get("codigo_remesa", f"#{remesa['id_remesa']}")
    cuerpo = _render(
        "remesa_generada.html",
        codigo_remesa=codigo,
        n_pegs=len(pegs),
        importe_total=f"{importe_total:.2f} €",
        fecha=datetime.now().strftime("%d/%m/%Y"),
        url=f"{settings.BASE_URL}/remesas/{remesa['id_remesa']}",
    )
    enviar_email(destinatarios, f"[SGPEG] Remesa en tramitación bancaria: {codigo}", cuerpo)


def notificar_remesa_cerrada(remesa: dict, pegs_pagados: list[dict]) -> None:
    from collections import defaultdict
    from datetime import datetime

    pegs_por_servicio: dict[int, list[dict]] = defaultdict(list)
    for peg in pegs_pagados:
        id_srv = peg.get("id_servicio")
        if id_srv:
            pegs_por_servicio[id_srv].append(peg)

    codigo = remesa.get("codigo_remesa", f"#{remesa['id_remesa']}")
    fecha_cierre = remesa.get("fecha_cierre", datetime.now().strftime("%d/%m/%Y"))
    url = f"{settings.BASE_URL}/remesas/{remesa['id_remesa']}"

    for u in mock_usuarios.listar_usuarios():
        if u["rol"] != "GESTOR_SERVICIO" or not u.get("email"):
            continue
        mis_pegs = pegs_por_servicio.get(u.get("id_servicio"), [])
        if not mis_pegs:
            continue
        total = sum(p.get("importe_total", 0) for p in mis_pegs)
        cuerpo = _render(
            "remesa_cerrada.html",
            codigo_remesa=codigo,
            pegs=mis_pegs,
            total=total,
            fecha_cierre=fecha_cierre,
            url=url,
        )
        enviar_email(u["email"], f"[SGPEG] Pagos ejecutados — {codigo}", cuerpo)
