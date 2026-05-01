from app.services import mock_mensajes, mock_usuarios


def enviar(
    id_emisor: int | None,
    id_destinatarios: list[int],
    asunto: str,
    cuerpo: str,
    tipo: str = "MANUAL",
    evento: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: int | None = None,
) -> list[dict]:
    return [
        mock_mensajes.crear_mensaje(
            id_emisor=id_emisor,
            id_destinatario=dest,
            asunto=asunto,
            cuerpo=cuerpo,
            tipo=tipo,
            evento=evento,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
        )
        for dest in id_destinatarios
    ]


def _ids_por_rol(*roles: str) -> list[int]:
    return [
        u["id_usuario"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] in roles
    ]


# ── Notificaciones automáticas ─────────────────────────────────────────────────

def notif_peg_creada(peg: dict) -> None:
    ids_ge = _ids_por_rol("GESTOR_ECONOMICO", "ADMIN")
    enviar(
        id_emisor=None,
        id_destinatarios=ids_ge,
        asunto=f"Nuevo PEG pendiente: {peg['codigo_peg']}",
        cuerpo=(
            f"Se ha registrado una nueva PEG pendiente de validación.\n\n"
            f"Código: {peg['codigo_peg']}\n"
            f"Descripción: {peg['descripcion_gasto']}\n"
            f"Importe: {peg['importe_total']:.2f} €"
        ),
        tipo="AUTO",
        evento="PEG_CREADA",
        entidad_tipo="PEG",
        entidad_id=peg["id_peg"],
    )


def notif_peg_validada(peg: dict, id_creador: int) -> None:
    enviar(
        id_emisor=None,
        id_destinatarios=[id_creador],
        asunto=f"PEG validada: {peg['codigo_peg']}",
        cuerpo=(
            f"Su propuesta de gasto ha sido validada y queda pendiente de tramitación.\n\n"
            f"Código: {peg['codigo_peg']}\n"
            f"Descripción: {peg['descripcion_gasto']}\n"
            f"Importe: {peg['importe_total']:.2f} €"
        ),
        tipo="AUTO",
        evento="PEG_VALIDADA",
        entidad_tipo="PEG",
        entidad_id=peg["id_peg"],
    )


def notif_peg_incidencia(peg: dict, id_creador: int, comentario: str = "") -> None:
    enviar(
        id_emisor=None,
        id_destinatarios=[id_creador],
        asunto=f"Incidencia en PEG: {peg['codigo_peg']}",
        cuerpo=(
            f"Se ha detectado una incidencia en su propuesta de gasto.\n\n"
            f"Código: {peg['codigo_peg']}\n"
            f"Descripción: {peg['descripcion_gasto']}"
            + (f"\n\nComentario del gestor:\n{comentario}" if comentario else "")
        ),
        tipo="AUTO",
        evento="PEG_INCIDENCIA",
        entidad_tipo="PEG",
        entidad_id=peg["id_peg"],
    )


def notif_peg_pagada(peg: dict, id_creador: int) -> None:
    enviar(
        id_emisor=None,
        id_destinatarios=[id_creador],
        asunto=f"PEG pagada: {peg['codigo_peg']}",
        cuerpo=(
            f"Su propuesta de gasto ha sido pagada.\n\n"
            f"Código: {peg['codigo_peg']}\n"
            f"Descripción: {peg['descripcion_gasto']}\n"
            f"Importe: {peg['importe_total']:.2f} €"
        ),
        tipo="AUTO",
        evento="PEG_PAGADA",
        entidad_tipo="PEG",
        entidad_id=peg["id_peg"],
    )


def notif_solicitud_autorizada(solicitud: dict) -> None:
    enviar(
        id_emisor=None,
        id_destinatarios=[solicitud["id_usuario_solicitante"]],
        asunto=f"Solicitud autorizada #{solicitud['id_solicitud']}",
        cuerpo=(
            f"Su solicitud de autorización previa al gasto ha sido aprobada.\n\n"
            f"Concepto: {solicitud['concepto']}\n"
            f"Importe estimado: {solicitud['importe_estimado']:.2f} €\n\n"
            f"Ya puede crear el PEG correspondiente."
        ),
        tipo="AUTO",
        evento="SOLICITUD_AUTORIZADA",
        entidad_tipo="SOLICITUD",
        entidad_id=solicitud["id_solicitud"],
    )


def notif_solicitud_denegada(solicitud: dict, motivo: str = "") -> None:
    enviar(
        id_emisor=None,
        id_destinatarios=[solicitud["id_usuario_solicitante"]],
        asunto=f"Solicitud denegada #{solicitud['id_solicitud']}",
        cuerpo=(
            f"Su solicitud de autorización previa al gasto ha sido denegada.\n\n"
            f"Concepto: {solicitud['concepto']}"
            + (f"\n\nMotivo:\n{motivo}" if motivo else "")
        ),
        tipo="AUTO",
        evento="SOLICITUD_DENEGADA",
        entidad_tipo="SOLICITUD",
        entidad_id=solicitud["id_solicitud"],
    )


def notif_remesa_cerrada(remesa: dict, peg_ids: list[int]) -> None:
    from app.services import pegs_service
    ids_servicios = {
        peg["id_servicio"]
        for pid in peg_ids
        if (peg := pegs_service.get_peg_raw(pid)) is not None
    }
    ids_gs = [
        u["id_usuario"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] == "GESTOR_SERVICIO" and u.get("id_servicio") in ids_servicios
    ]
    if not ids_gs:
        return
    enviar(
        id_emisor=None,
        id_destinatarios=ids_gs,
        asunto=f"Remesa pagada: {remesa.get('codigo_remesa', '')}",
        cuerpo=(
            f"La remesa de transferencias {remesa.get('codigo_remesa', '')} ha sido cerrada.\n\n"
            f"Los PEGs de su servicio han sido marcados como PAGADO."
        ),
        tipo="AUTO",
        evento="REMESA_PAGADA",
        entidad_tipo="REMESA",
        entidad_id=remesa["id_remesa"],
    )


def notif_remesa_directa_cerrada(remesa: dict) -> None:
    from app.services.remesas_directas_service import obtener_remesa
    remesa_full = obtener_remesa(remesa["id_remesa"]) or remesa
    ids_servicios = {
        g.get("id_servicio")
        for g in remesa_full.get("gastos", [])
        if g.get("id_servicio")
    }
    ids_gs = [
        u["id_usuario"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] == "GESTOR_SERVICIO" and u.get("id_servicio") in ids_servicios
    ]
    if not ids_gs:
        return
    enviar(
        id_emisor=None,
        id_destinatarios=ids_gs,
        asunto=f"Remesa directa cerrada: {remesa.get('codigo_remesa', '')}",
        cuerpo=(
            f"La remesa de gastos directos {remesa.get('codigo_remesa', '')} ha sido cerrada.\n\n"
            f"Los gastos de su servicio han quedado registrados."
        ),
        tipo="AUTO",
        evento="REMESA_DIRECTA_PAGADA",
        entidad_tipo="REMESA_DIRECTA",
        entidad_id=remesa["id_remesa"],
    )
