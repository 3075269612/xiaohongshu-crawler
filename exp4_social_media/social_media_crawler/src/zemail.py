from __future__ import annotations

import smtplib
from email.message import EmailMessage


def send_email(config: dict, subject: str, body: str) -> bool:
    if not config.get("enabled"):
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["sender"]
    message["To"] = config["receiver"]
    message.set_content(body)

    with smtplib.SMTP_SSL(config["smtp_host"], int(config.get("smtp_port", 465))) as smtp:
        smtp.login(config["sender"], config["password"])
        smtp.send_message(message)
    return True