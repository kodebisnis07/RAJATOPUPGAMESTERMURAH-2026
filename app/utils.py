import logging
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from flask import current_app, url_for
from werkzeug.utils import secure_filename

from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "ico", "svg"}
logger = logging.getLogger(__name__)


def slugify(value):
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or datetime.now().strftime("item-%Y%m%d%H%M%S")


def unique_slug(model, name, current_id=None):
    base = slugify(name)
    slug = base
    counter = 2
    while True:
        query = model.query.filter_by(slug=slug)
        if current_id:
            query = query.filter(model.id != current_id)
        if not query.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _cloudinary_credentials():
    """Read Cloudinary credentials from CLOUDINARY_URL or separate variables."""
    cloudinary_url = (current_app.config.get("CLOUDINARY_URL") or "").strip()
    if cloudinary_url:
        parsed = urlparse(cloudinary_url)
        if parsed.scheme == "cloudinary" and parsed.username and parsed.password and parsed.hostname:
            return {
                "cloud_name": parsed.hostname,
                "api_key": unquote(parsed.username),
                "api_secret": unquote(parsed.password),
            }

    cloud_name = (current_app.config.get("CLOUDINARY_CLOUD_NAME") or "").strip()
    api_key = (current_app.config.get("CLOUDINARY_API_KEY") or "").strip()
    api_secret = (current_app.config.get("CLOUDINARY_API_SECRET") or "").strip()
    if cloud_name and api_key and api_secret:
        return {"cloud_name": cloud_name, "api_key": api_key, "api_secret": api_secret}
    return None


def _media_backend():
    backend = (current_app.config.get("MEDIA_STORAGE_BACKEND") or "auto").strip().lower()
    if backend not in {"auto", "local", "cloudinary"}:
        backend = "auto"
    return backend


def _cloudinary_enabled():
    backend = _media_backend()
    credentials = _cloudinary_credentials()
    if backend == "cloudinary" and not credentials:
        raise ValueError(
            "Cloudinary belum dikonfigurasi. Isi CLOUDINARY_URL pada Environment Render, "
            "kemudian deploy ulang."
        )
    return backend == "cloudinary" or (backend == "auto" and bool(credentials))


def _cloudinary_folder(local_folder):
    root_folder = (current_app.config.get("CLOUDINARY_FOLDER") or "rajatopupgames").strip("/ ") or "rajatopupgames"
    leaf = Path(local_folder).name if local_folder else "uploads"
    leaf = slugify(leaf).replace("-", "_")
    return f"{root_folder}/{leaf}"


def save_uploaded_image(file, folder):
    """Save uploads permanently to Cloudinary when configured.

    Database value:
    - Cloudinary production: permanent HTTPS URL.
    - Local development/legacy: filename in the existing static folder.
    """
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        raise ValueError("Format gambar harus png, jpg, jpeg, webp, gif, ico, atau svg")

    if _cloudinary_enabled():
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(**_cloudinary_credentials(), secure=True)
            try:
                file.stream.seek(0)
            except Exception:
                pass
            result = cloudinary.uploader.upload(
                file.stream,
                folder=_cloudinary_folder(folder),
                resource_type="image",
                use_filename=True,
                unique_filename=True,
                overwrite=False,
            )
            secure_url = result.get("secure_url")
            if not secure_url:
                raise RuntimeError("Cloudinary tidak mengembalikan URL gambar")
            return secure_url
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Cloudinary upload failed")
            raise ValueError(f"Upload gambar ke Cloudinary gagal: {exc}") from exc

    os.makedirs(folder, exist_ok=True)
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    final_name = f"{slugify(name)}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext.lower()}"
    file.save(os.path.join(folder, final_name))
    return final_name


def is_remote_media(value):
    value = (value or "").strip().lower()
    return value.startswith("https://") or value.startswith("http://") or value.startswith("//")


def media_url(value, local_subfolder="products"):
    """Build a display URL for both permanent cloud URLs and old local filenames."""
    value = (value or "").strip()
    if not value:
        return None
    if is_remote_media(value) or value.startswith("data:"):
        return value

    clean = value.lstrip("/")
    if clean.startswith("static/"):
        clean = clean[len("static/"):]
    elif clean.startswith("img/"):
        pass
    elif "/" in clean:
        clean = f"img/{clean}"
    else:
        clean = f"img/{local_subfolder.strip('/')}/{clean}"
    return url_for("static", filename=clean)


def build_image_url(value, folder="img/site"):
    """Backward-compatible helper used by the site-logo templates."""
    subfolder = (folder or "img/site").strip("/")
    if subfolder.startswith("img/"):
        subfolder = subfolder[4:]
    return media_url(value, subfolder)


def _cloudinary_public_id(url):
    try:
        path_parts = [part for part in urlparse(url).path.split("/") if part]
        upload_index = path_parts.index("upload")
        tail = path_parts[upload_index + 1:]
        for index, part in enumerate(tail):
            if re.fullmatch(r"v\d+", part):
                tail = tail[index + 1:]
                break
        if not tail:
            return None
        tail[-1] = os.path.splitext(tail[-1])[0]
        return unquote("/".join(tail))
    except (ValueError, IndexError):
        return None


def delete_uploaded_image(value, folder):
    """Delete an old image from Cloudinary or a legacy local folder."""
    value = (value or "").strip()
    if not value:
        return

    if is_remote_media(value):
        public_id = _cloudinary_public_id(value)
        credentials = _cloudinary_credentials()
        if not public_id or not credentials:
            return
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(**credentials, secure=True)
            cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
        except Exception:
            logger.exception("Cloudinary delete failed for %s", public_id)
        return

    try:
        base = Path(folder).resolve()
        target = (base / Path(value).name).resolve()
        if target.parent == base and target.exists():
            target.unlink()
    except OSError:
        logger.exception("Local image delete failed for %s", value)


def delete_uploaded_image_file(value, folder):
    """Backward-compatible alias used by the logo/favicon settings route."""
    delete_uploaded_image(value, folder)

def get_setting(key, default=None):
    from app.models import Setting
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting and setting.value not in (None, "") else default


def set_setting(key, value):
    from app.models import Setting
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        setting = Setting(key=key)
        db.session.add(setting)
    setting.value = value
    return setting


def is_wallet_order(order):
    """Cek apakah order dibayar memakai saldo internal RajaTopup."""
    payment_method = (getattr(order, "payment_method", None) or "").lower()
    payment = getattr(order, "payment", None)
    payment_provider = (getattr(payment, "provider", None) or "").lower() if payment else ""
    payment_code = (getattr(payment, "payment_code", None) or "").lower() if payment else ""
    payment_name = (getattr(payment, "payment_name", None) or "").lower() if payment else ""
    payment_reference = (getattr(order, "payment_reference", None) or "").lower()

    return (
        "saldo" in payment_method
        or payment_provider == "wallet"
        or payment_code == "saldo"
        or "saldo" in payment_name
        or payment_reference == "wallet"
    )


def refund_wallet_order(order, reason="Pesanan dibatalkan"):
    """
    Kembalikan saldo user untuk order yang dibayar dengan saldo internal.
    Fungsi ini tidak melakukan db.session.commit(), supaya aman dipakai di route mana pun.
    Return: nominal refund jika berhasil, 0 jika tidak perlu/tidak bisa refund.
    """
    from app.models import UserNotification

    if not order or not getattr(order, "user", None):
        return 0
    if not is_wallet_order(order):
        return 0

    # Refund hanya untuk pembayaran saldo yang sudah terpotong/paid.
    payment = getattr(order, "payment", None)
    paid_by_wallet = (
        (getattr(order, "payment_status", None) == "paid")
        or (payment and getattr(payment, "status", None) == "paid")
        or is_wallet_order(order)
    )
    if not paid_by_wallet:
        return 0

    amount = int((getattr(payment, "amount", None) if payment else None) or getattr(order, "price", 0) or 0)
    if amount <= 0:
        return 0

    order.user.balance = int(order.user.balance or 0) + amount
    db.session.add(UserNotification(
        user_id=order.user_id,
        order_id=order.id,
        title="Saldo dikembalikan",
        message=f"Saldo Rp {amount:,} dari pesanan {order.invoice} sudah dikembalikan. {reason}.",
        type="wallet_refund",
    ))
    return amount
