import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def enviar_email(destinatario: str | list[str], asunto: str, cuerpo_html: str) -> bool:
    """
    Envía un correo HTML usando SMTP.
    Devuelve True si el envío fue correcto, False si falló (sin lanzar excepción).
    """
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        logger.warning("SMTP no configurado — correo no enviado: %s", asunto)
        return False

    destinatarios = [destinatario] if isinstance(destinatario, str) else destinatario
    destinatarios = [d for d in destinatarios if d]  # descartar vacíos
    if not destinatarios:
        logger.warning("Sin destinatarios válidos para: %s", asunto)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = settings.SMTP_FROM
    msg["To"] = ", ".join(destinatarios)
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as servidor:
            servidor.ehlo()
            if servidor.has_extn("STARTTLS"):
                servidor.starttls()
                servidor.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                servidor.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            servidor.sendmail(settings.SMTP_FROM, destinatarios, msg.as_string())
        logger.info("Correo enviado a %s — %s", destinatarios, asunto)
        return True
    except Exception:
        logger.exception("Error al enviar correo '%s' a %s", asunto, destinatarios)
        return False
