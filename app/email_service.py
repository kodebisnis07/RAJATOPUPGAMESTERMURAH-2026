"""Pengiriman email transaksional sederhana melalui SMTP."""
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app


def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> tuple[bool, str | None]:
    """Kirim email menggunakan konfigurasi MAIL_*.

    Mengembalikan (berhasil, pesan_error). Detail error hanya untuk log server.
    """
    config = current_app.config
    server = (config.get("MAIL_SERVER") or "").strip()
    username = (config.get("MAIL_USERNAME") or "").strip()
    password = config.get("MAIL_PASSWORD") or ""
    sender = (config.get("MAIL_DEFAULT_SENDER") or username).strip()
    port = int(config.get("MAIL_PORT") or 587)
    use_tls = bool(config.get("MAIL_USE_TLS", True))
    use_ssl = bool(config.get("MAIL_USE_SSL", False))

    if not server or not sender:
        return False, "MAIL_SERVER atau MAIL_DEFAULT_SENDER belum dikonfigurasi"

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, timeout=20, context=context) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(server, port, timeout=20) as smtp:
                smtp.ehlo()
                if use_tls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        return True, None
    except Exception as exc:  # detail hanya dicatat di server
        return False, str(exc)


def send_password_reset_email(user, reset_url: str, expires_minutes: int = 60) -> tuple[bool, str | None]:
    site_name = current_app.config.get("SITE_NAME", "Raja Topup Games")
    subject = f"Atur ulang password akun {site_name}"
    text_body = f"""Halo {user.name or user.username},

Kami menerima permintaan untuk mengatur ulang password akun Anda.

Buka link berikut untuk membuat password baru:
{reset_url}

Link ini berlaku selama {expires_minutes} menit dan hanya dapat digunakan untuk akun Anda.
Jika Anda tidak meminta perubahan password, abaikan email ini.

{site_name}
"""
    html_body = f"""
<!doctype html>
<html lang="id">
  <body style="margin:0;background:#f4f6f8;font-family:Arial,sans-serif;color:#18202a">
    <div style="max-width:560px;margin:32px auto;background:#ffffff;border-radius:12px;padding:32px;box-shadow:0 6px 20px rgba(0,0,0,.08)">
      <h2 style="margin-top:0">Atur ulang password</h2>
      <p>Halo <strong>{user.name or user.username}</strong>,</p>
      <p>Kami menerima permintaan untuk mengatur ulang password akun Anda.</p>
      <p style="margin:28px 0">
        <a href="{reset_url}" style="background:#e11d48;color:#fff;text-decoration:none;padding:13px 22px;border-radius:8px;display:inline-block;font-weight:bold">Buat Password Baru</a>
      </p>
      <p style="font-size:14px;color:#5f6b78">Link berlaku selama {expires_minutes} menit. Jika Anda tidak meminta perubahan password, abaikan email ini.</p>
      <hr style="border:none;border-top:1px solid #e8ebef;margin:24px 0">
      <p style="font-size:13px;color:#7b8794">{site_name}</p>
    </div>
  </body>
</html>
"""
    return send_email(user.email, subject, text_body, html_body)
