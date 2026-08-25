from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from urllib import error, request

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "mock").lower()
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@localhost")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


class EmailDeliveryError(RuntimeError):
    pass


def _build_temp_password_body(username: str, temp_password: str, organization_name: str) -> str:
    return (
        f"Hello {username},\n\n"
        f"You have been invited to join {organization_name}.\n"
        f"Your temporary password is: {temp_password}\n\n"
        "Please sign in and reset this password immediately.\n"
    )


def mock_send_email(recipient: str, subject: str, body: str) -> dict:
    return {"provider": "mock", "status": "queued", "recipient": recipient, "subject": subject, "body": body}


def smtp_send_email(recipient: str, subject: str, body: str) -> dict:
    if not SMTP_HOST:
        raise EmailDeliveryError("SMTP_HOST is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USE_TLS:
            server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    return {"provider": "smtp", "status": "sent", "recipient": recipient, "subject": subject}


def sendgrid_send_email(recipient: str, subject: str, body: str) -> dict:
    if not SENDGRID_API_KEY:
        raise EmailDeliveryError("SENDGRID_API_KEY is not configured")

    payload = json.dumps({
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }).encode("utf-8")

    req = request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            return {"provider": "sendgrid", "status": "sent", "recipient": recipient, "subject": subject, "http_status": response.status}
    except error.HTTPError as exc:
        raise EmailDeliveryError(f"SendGrid delivery failed: {exc.read().decode('utf-8', 'ignore')}") from exc


def send_temp_password_email(recipient: str, username: str, temp_password: str, organization_name: str) -> dict:
    subject = f"Your temporary password for {organization_name}"
    body = _build_temp_password_body(username, temp_password, organization_name)

    if EMAIL_PROVIDER == "smtp":
        return smtp_send_email(recipient, subject, body)
    if EMAIL_PROVIDER == "sendgrid":
        return sendgrid_send_email(recipient, subject, body)
    return mock_send_email(recipient, subject, body)
