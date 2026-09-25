import os
import smtplib
from email.message import EmailMessage


def enviar_email(destinatario, asunto, contenido_html, contenido_texto=None):
    """
    Envía un correo mediante SMTP.

    Devuelve:
        True  -> enviado correctamente
        False -> error durante el envío
    """

    servidor = os.getenv("SMTP_HOST")
    puerto = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    remitente = os.getenv("SMTP_FROM") or usuario

    if not servidor or not usuario or not password or not remitente:
        print("EMAIL: configuración SMTP incompleta.")
        return False

    mensaje = EmailMessage()

    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    if contenido_texto:
        mensaje.set_content(contenido_texto)
    else:
        mensaje.set_content(
            "Este correo contiene contenido HTML. "
            "Abrilo con un cliente compatible."
        )

    mensaje.add_alternative(
        contenido_html,
        subtype="html"
    )

    try:
        with smtplib.SMTP(servidor, puerto, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(usuario, password)
            smtp.send_message(mensaje)

        return True

    except Exception as error:
        print(f"EMAIL: error al enviar correo: {error}")
        return False


def preparar_confirmacion_pago(participacion):
    """
    Prepara los datos necesarios para el correo de pago confirmado.
    No envía ningún correo.
    """
    from flask import render_template
    from models.sorteo import Sorteo
    from models.numero import Numero

    sorteo = Sorteo.query.get(participacion.sorteo_id)

    numeros = (
        Numero.query
        .filter_by(
            participacion_id=participacion.id,
            sorteo_id=participacion.sorteo_id
        )
        .order_by(Numero.numero.asc())
        .all()
    )

    lista_numeros = ", ".join(
        str(numero.numero)
        for numero in numeros
    )

    html = render_template(
        "emails/pago_confirmado.html",
        nombre=participacion.nombre,
        sorteo=sorteo.titulo if sorteo else "Sorteo",
        numeros=lista_numeros or "Sin números asignados"
    )

    asunto = (
        f"Pago confirmado - "
        f"{sorteo.titulo if sorteo else 'Paranacito Pesca'}"
    )

    return {
        "destinatario": participacion.email,
        "asunto": asunto,
        "html": html,
        "numeros": lista_numeros
    }
