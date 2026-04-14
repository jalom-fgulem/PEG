"""
Notificaciones por correo electrónico para el ciclo de vida de las PEGs.
Obtiene los emails de gestores filtrando los usuarios en memoria por rol.

Configuración SMTP → app/core/config.py (o variables de entorno en .env):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, BASE_URL
"""
from app.core.email import enviar_email
from app.services import mock_usuarios
from app.core.config import settings


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ──────────────────────────────────────────────────────────────────────────────

def _emails_gestores() -> list[str]:
    """Devuelve los emails de todos los usuarios con rol GESTOR_ECONOMICO."""
    return [
        u["email"]
        for u in mock_usuarios.listar_usuarios()
        if u["rol"] == "GESTOR_ECONOMICO" and u.get("email")
    ]


def _linea() -> str:
    return "─" * 60


def _pie() -> str:
    return (
        "<br><br>"
        "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0'>"
        "<p style='color:#6e6a73;font-size:0.88rem;margin:0'>"
        "SGPEG · Sistema de Gestión de Propuestas Específicas de Gasto<br>"
        "FGULEM · Fundación General de la Universidad de León"
        "</p>"
    )


def _wrap(contenido: str) -> str:
    """Envuelve el contenido en un HTML mínimo con los colores corporativos."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             background:#f7f7f8;color:#4f4c55;margin:0;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
              border:1px solid #e5e7eb;padding:32px 28px;">
    <p style="margin:0 0 20px;font-size:0.9rem;color:#6e6a73;font-weight:700;
              letter-spacing:0.06em;text-transform:uppercase;">SGPEG</p>
    {contenido}
    {_pie()}
  </div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICACIONES
# ──────────────────────────────────────────────────────────────────────────────

def enviar_notificacion_nuevo_peg(peg: dict, usuario_creador: dict) -> bool:
    """
    Notifica a todos los GESTOR_ECONOMICO de una nueva PEG pendiente de validación.
    Devuelve True si al menos un correo se envió correctamente, False en caso contrario.
    """
    destinatarios = _emails_gestores()
    if not destinatarios:
        print("[SGPEG] Sin gestores económicos con email configurado — notificación omitida.")
        return False

    codigo = peg["codigo_peg"]
    id_peg = peg["id_peg"]
    servicio = peg.get("nombre_servicio", "")
    proveedor = peg.get("nombre_proveedor", "")
    importe = f"{peg['importe_total']:.2f} €"
    descripcion = peg["descripcion_gasto"]
    creado_por = usuario_creador.get("nombre_completo", usuario_creador.get("username", ""))
    url_peg = f"{settings.BASE_URL}/pegs/{id_peg}"

    asunto = f"[SGPEG] Nuevo PEG pendiente de validación: {codigo}"
    cuerpo = _wrap(f"""
        <h2 style="margin:0 0 8px;color:#c21b84;font-size:1.3rem;">Nueva PEG pendiente de validación</h2>
        <p style="margin:0 0 20px;color:#6e6a73;">
          Se ha registrado una nueva propuesta de gasto que requiere su revisión.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:0.95rem;">
          <tr>
            <td style="padding:8px 0;color:#6e6a73;width:40%">Código</td>
            <td style="padding:8px 0;font-weight:700">{codigo}</td>
          </tr>
          <tr style="background:#f7f7f8">
            <td style="padding:8px 6px;color:#6e6a73">Servicio</td>
            <td style="padding:8px 6px">{servicio}</td>
          </tr>
          <tr>
            <td style="padding:8px 0;color:#6e6a73">Proveedor</td>
            <td style="padding:8px 0">{proveedor}</td>
          </tr>
          <tr style="background:#f7f7f8">
            <td style="padding:8px 6px;color:#6e6a73">Importe total</td>
            <td style="padding:8px 6px;font-weight:700">{importe}</td>
          </tr>
          <tr>
            <td style="padding:8px 0;color:#6e6a73">Descripción</td>
            <td style="padding:8px 0">{descripcion}</td>
          </tr>
          <tr style="background:#f7f7f8">
            <td style="padding:8px 6px;color:#6e6a73">Creado por</td>
            <td style="padding:8px 6px">{creado_por}</td>
          </tr>
        </table>
        <p style="margin:28px 0 0;text-align:center;">
          <a href="{url_peg}"
             style="display:inline-block;background:#c21b84;color:#fff;
                    font-weight:700;font-size:0.97rem;text-decoration:none;
                    padding:12px 28px;border-radius:10px;">
            Revisar y validar este PEG
          </a>
        </p>
    """)

    ok = enviar_email(destinatarios, asunto, cuerpo)
    if not ok:
        print(f"[SGPEG] No se pudo enviar notificación de nuevo PEG {codigo} a {destinatarios}")
    return ok


def notificar_peg_creada(peg: dict, usuario_solicitante: dict) -> None:
    """
    Correo al solicitante confirmando recepción.
    Correo a gestores avisando de nueva PEG pendiente de revisión.
    """
    codigo = peg["codigo_peg"]
    descripcion = peg["descripcion_gasto"]
    importe = f"{peg['importe_total']:.2f} €"
    servicio = peg.get("nombre_servicio", "")
    proveedor = peg.get("nombre_proveedor", "")

    # — Correo al solicitante —
    email_sol = usuario_solicitante.get("email")
    if email_sol:
        cuerpo_sol = _wrap(f"""
            <h2 style="margin:0 0 8px;color:#c21b84;font-size:1.3rem;">PEG registrada correctamente</h2>
            <p style="margin:0 0 20px;color:#6e6a73;">Su propuesta de gasto ha sido recibida y está pendiente de revisión.</p>
            <table style="width:100%;border-collapse:collapse;font-size:0.95rem;">
              <tr><td style="padding:8px 0;color:#6e6a73;width:40%">Código</td>
                  <td style="padding:8px 0;font-weight:700">{codigo}</td></tr>
              <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Descripción</td>
                  <td style="padding:8px 6px">{descripcion}</td></tr>
              <tr><td style="padding:8px 0;color:#6e6a73">Proveedor</td>
                  <td style="padding:8px 0">{proveedor}</td></tr>
              <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Importe total</td>
                  <td style="padding:8px 6px;font-weight:700">{importe}</td></tr>
              <tr><td style="padding:8px 0;color:#6e6a73">Servicio</td>
                  <td style="padding:8px 0">{servicio}</td></tr>
            </table>
            <p style="margin:20px 0 0;color:#6e6a73;font-size:0.93rem;">
              Recibirá una notificación cuando su propuesta sea validada o si se detecta alguna incidencia.
            </p>
        """)
        enviar_email(email_sol, f"[SGPEG] PEG recibida: {codigo}", cuerpo_sol)

    # — Correo a gestores —
    enviar_notificacion_nuevo_peg(peg, usuario_solicitante)


def notificar_peg_validada(peg: dict, email_solicitante: str) -> None:
    """Avisa al solicitante de que su PEG ha sido validada."""
    codigo = peg["codigo_peg"]
    importe = f"{peg['importe_total']:.2f} €"
    cuerpo = _wrap(f"""
        <h2 style="margin:0 0 8px;color:#7faa55;font-size:1.3rem;">PEG validada</h2>
        <p style="margin:0 0 20px;color:#6e6a73;">
          Su propuesta de gasto <strong>{codigo}</strong> ha sido revisada y <strong>validada</strong>.
          Queda pendiente de tramitación para pago.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:0.95rem;">
          <tr><td style="padding:8px 0;color:#6e6a73;width:40%">Código</td>
              <td style="padding:8px 0;font-weight:700">{codigo}</td></tr>
          <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Descripción</td>
              <td style="padding:8px 6px">{peg['descripcion_gasto']}</td></tr>
          <tr><td style="padding:8px 0;color:#6e6a73">Importe total</td>
              <td style="padding:8px 0;font-weight:700">{importe}</td></tr>
        </table>
    """)
    enviar_email(email_solicitante, f"[SGPEG] PEG validada: {codigo}", cuerpo)


def notificar_peg_incidencia(
    peg: dict,
    email_solicitante: str,
    descripcion_incidencia: str,
) -> None:
    """Avisa al solicitante de que su PEG tiene una incidencia que resolver."""
    codigo = peg["codigo_peg"]
    cuerpo = _wrap(f"""
        <h2 style="margin:0 0 8px;color:#c21b84;font-size:1.3rem;">Incidencia en su PEG</h2>
        <p style="margin:0 0 20px;color:#6e6a73;">
          Se ha detectado una incidencia en su propuesta de gasto <strong>{codigo}</strong>
          que requiere su atención.
        </p>
        <div style="background:#fff3f9;border-left:4px solid #c21b84;
                    border-radius:0 12px 12px 0;padding:14px 16px;margin-bottom:20px;">
          <p style="margin:0;font-size:0.95rem;color:#4f4c55;">{descripcion_incidencia}</p>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:0.95rem;">
          <tr><td style="padding:8px 0;color:#6e6a73;width:40%">Código</td>
              <td style="padding:8px 0;font-weight:700">{codigo}</td></tr>
          <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Descripción</td>
              <td style="padding:8px 6px">{peg['descripcion_gasto']}</td></tr>
        </table>
        <p style="margin:20px 0 0;color:#6e6a73;font-size:0.93rem;">
          Por favor, contacte con el equipo gestor para resolverla.
        </p>
    """)
    enviar_email(email_solicitante, f"[SGPEG] Incidencia en PEG: {codigo}", cuerpo)


def notificar_peg_pagada(peg: dict, email_solicitante: str) -> None:
    """Avisa al solicitante de que su PEG ha sido pagada."""
    codigo = peg["codigo_peg"]
    importe = f"{peg['importe_total']:.2f} €"
    cuerpo = _wrap(f"""
        <h2 style="margin:0 0 8px;color:#2f7a55;font-size:1.3rem;">PEG pagada</h2>
        <p style="margin:0 0 20px;color:#6e6a73;">
          La propuesta de gasto <strong>{codigo}</strong> ha sido <strong>pagada</strong>.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:0.95rem;">
          <tr><td style="padding:8px 0;color:#6e6a73;width:40%">Código</td>
              <td style="padding:8px 0;font-weight:700">{codigo}</td></tr>
          <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Descripción</td>
              <td style="padding:8px 6px">{peg['descripcion_gasto']}</td></tr>
          <tr><td style="padding:8px 0;color:#6e6a73">Importe total</td>
              <td style="padding:8px 0;font-weight:700">{importe}</td></tr>
          <tr style="background:#f7f7f8"><td style="padding:8px 6px;color:#6e6a73">Proveedor</td>
              <td style="padding:8px 6px">{peg.get('nombre_proveedor', '')}</td></tr>
        </table>
    """)
    enviar_email(email_solicitante, f"[SGPEG] PEG pagada: {codigo}", cuerpo)
