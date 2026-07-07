import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from app.extensions import db

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


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


def save_uploaded_image(file, folder):
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        raise ValueError("Format gambar harus png, jpg, jpeg, webp, atau gif")

    os.makedirs(folder, exist_ok=True)
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    final_name = f"{slugify(name)}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext.lower()}"
    file.save(os.path.join(folder, final_name))
    return final_name


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

