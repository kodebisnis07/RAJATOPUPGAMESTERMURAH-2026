from datetime import datetime, timedelta
import hashlib
import hmac
import requests
from app.extensions import db
from app.models import Payment
from app.utils import get_setting


def create_payment(order):
    provider = (get_setting("payment_gateway", "manual") or "manual").lower()
    if provider == "tripay":
        return create_tripay_payment(order)
    if provider in {"duitku", "xendit"}:
        return create_placeholder_payment(order, provider)
    return create_placeholder_payment(order, "manual")


def create_placeholder_payment(order, provider="manual"):
    payment = Payment(
        order_id=order.id,
        payment_code=order.payment_method or provider.upper(),
        payment_name=(order.payment_method or provider.upper()),
        provider=provider,
        reference=order.invoice,
        checkout_url=None,
        amount=order.price,
        status="pending",
        expired_at=datetime.utcnow() + timedelta(minutes=10),
    )
    order.payment_reference = payment.reference
    db.session.add(payment)
    db.session.commit()
    return payment


def create_tripay_payment(order):
    api_key = get_setting("tripay_api_key")
    private_key = get_setting("tripay_private_key")
    merchant_code = get_setting("tripay_merchant_code")
    mode = get_setting("tripay_mode", "sandbox")

    if not api_key or not private_key or not merchant_code:
        return create_placeholder_payment(order, "tripay")

    base_url = "https://tripay.co.id/api-sandbox" if mode == "sandbox" else "https://tripay.co.id/api"
    signature = hmac.new(
        private_key.encode(),
        f"{merchant_code}{order.invoice}{order.price}".encode(),
        hashlib.sha256,
    ).hexdigest()

    payload = {
        "method": order.payment_method or "QRIS",
        "merchant_ref": order.invoice,
        "amount": order.price,
        "customer_name": order.customer_name or "Pelanggan Raja Topup",
        "customer_email": order.customer_email or "customer@example.com",
        "customer_phone": order.customer_phone or "080000000000",
        "order_items": [{"name": order.product.name, "price": order.price, "quantity": 1}],
        "expired_time": int((datetime.utcnow() + timedelta(minutes=10)).timestamp()),
        "signature": signature,
    }

    try:
        response = requests.post(
            f"{base_url}/transaction/create",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        data = response.json()
        if not data.get("success"):
            return create_placeholder_payment(order, "tripay")
        trx = data.get("data", {})
    except Exception:
        return create_placeholder_payment(order, "tripay")

    payment = Payment(
        order_id=order.id,
        payment_code=trx.get("pay_code") or trx.get("qr_string"),
        payment_name=order.payment_method or "Tripay",
        provider="tripay",
        reference=trx.get("reference"),
        checkout_url=trx.get("checkout_url"),
        qr_url=trx.get("qr_url"),
        amount=order.price,
        status="pending",
        expired_at=datetime.utcfromtimestamp(trx["expired_time"]) if trx.get("expired_time") else None,
    )
    order.payment_url = payment.checkout_url
    order.payment_reference = payment.reference
    db.session.add(payment)
    db.session.commit()
    return payment
