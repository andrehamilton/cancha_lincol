"""Envio de codigos usando una cuenta SMTP configurada fuera del codigo."""

import os
import smtplib
from email.message import EmailMessage


def send_verification_code(recipient, code):
    sender = os.environ.get("CANCHA_SMTP_USER", "").strip()
    app_password = os.environ.get("CANCHA_SMTP_APP_PASSWORD", "").strip()
    if not sender or not app_password:
        raise RuntimeError("Falta configurar CANCHA_SMTP_USER y CANCHA_SMTP_APP_PASSWORD.")

    message = EmailMessage()
    message["Subject"] = "Codigo de verificacion de Cancha"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Tu codigo de verificacion de Cancha es: {code}\n\n"
        "Ingresalo en el formulario para confirmar tu cuenta."
    )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(sender, app_password)
        server.send_message(message)
