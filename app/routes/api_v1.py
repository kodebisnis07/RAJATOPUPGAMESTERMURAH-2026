import secrets
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models import ApiClient, ApiOrder, ApiRequestLog, Product, Order

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

def _json(message, status=200, **data):
    payload = {"success": 200 <= status < 300, "message": message}
    payload.update(data)
    return jsonify(payload), status

def _log(client, status, message):
    try:
        db.session.add(ApiRequestLog(client_id=client.id if client else None, method=request.method, endpoint=request.path, status_code=status, ip_address=request.headers.get("X-Forwarded-For", request.remote_addr), response_message=str(message)[:255]))
        db.session.commit()
    except Exception:
        db.session.rollback()

def api_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        raw_key = auth[7:].strip() if auth.lower().startswith("bearer ") else request.headers.get("X-API-Key", "").strip()
        raw_secret = request.headers.get("X-API-Secret", "").strip()
        if not raw_key or not raw_secret:
            _log(None, 401, "API key/secret tidak lengkap")
            return _json("API key dan API secret wajib dikirim.", 401)
        prefix = raw_key.split("_", 2)[0:2]
        prefix = "_".join(prefix) if len(prefix) == 2 else raw_key[:20]
        client = ApiClient.query.filter_by(key_prefix=prefix).first()
        if not client or client.status != "active" or not client.check_api_key(raw_key) or not client.check_api_secret(raw_secret):
            _log(client, 401, "Kredensial tidak valid")
            return _json("Kredensial API tidak valid atau akun nonaktif.", 401)
        allowed = [x.strip() for x in (client.allowed_ips or "").replace("\n", ",").split(",") if x.strip()]
        remote_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        if allowed and remote_ip not in allowed:
            _log(client, 403, "IP tidak diizinkan")
            return _json("Alamat IP tidak diizinkan.", 403)
        g.api_client = client
        return view(*args, **kwargs)
    return wrapped

@api_v1_bp.get("/ping")
def ping():
    return _json("API Raja Topup Games aktif.", version="1.0")

@api_v1_bp.get("/balance")
@api_auth
def balance():
    _log(g.api_client, 200, "OK")
    return _json("Saldo berhasil diambil.", balance=int(g.api_client.balance or 0))

@api_v1_bp.get("/products")
@api_auth
def products():
    items = Product.query.filter_by(status="active").order_by(Product.category_id.asc(), Product.price.asc()).all()
    markup = max(0, int(g.api_client.price_markup_percent or 0))
    data = []
    for item in items:
        base = int(item.price or 0)
        api_price = base + int(base * markup / 100)
        data.append({"id": item.id, "code": item.provider_code or item.slug, "name": item.name, "category": item.category.name if item.category else None, "price": api_price, "stock": int(item.stock or 0), "status": item.status})
    _log(g.api_client, 200, "OK")
    return _json("Daftar produk berhasil diambil.", products=data)

@api_v1_bp.post("/order")
@api_auth
def create_order():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    external_ref = str(data.get("external_ref") or "").strip()
    game_user_id = str(data.get("user_id") or "").strip()
    server_id = str(data.get("server_id") or "").strip() or None
    if not product_id or not external_ref or not game_user_id:
        _log(g.api_client, 422, "Data order tidak lengkap")
        return _json("product_id, external_ref, dan user_id wajib diisi.", 422)
    existing = ApiOrder.query.filter_by(client_id=g.api_client.id, external_ref=external_ref).first()
    if existing:
        _log(g.api_client, 200, "Idempotent order")
        return _json("Order dengan external_ref ini sudah ada.", order={"invoice": existing.order.invoice, "external_ref": existing.external_ref, "status": existing.order.order_status, "payment_status": existing.order.payment_status, "amount": existing.charged_amount})
    product = Product.query.filter_by(id=product_id, status="active").first()
    if not product:
        _log(g.api_client, 404, "Produk tidak ditemukan")
        return _json("Produk tidak ditemukan atau nonaktif.", 404)
    base = int(product.price or 0)
    amount = base + int(base * max(0, int(g.api_client.price_markup_percent or 0)) / 100)
    if int(g.api_client.balance or 0) < amount:
        _log(g.api_client, 402, "Saldo tidak cukup")
        return _json("Saldo mitra tidak mencukupi.", 402, balance=int(g.api_client.balance or 0), required=amount)
    invoice = "API-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3).upper()
    try:
        order = Order(invoice=invoice, product_id=product.id, customer_name=g.api_client.name, customer_email=g.api_client.contact_email, game_user_id=game_user_id, game_server_id=server_id, price=amount, payment_method="Saldo Mitra API", payment_status="paid", order_status="processing")
        g.api_client.balance = int(g.api_client.balance or 0) - amount
        db.session.add(order)
        db.session.flush()
        db.session.add(ApiOrder(client_id=g.api_client.id, order_id=order.id, external_ref=external_ref, charged_amount=amount))
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log(g.api_client, 500, "Gagal membuat order")
        return _json("Order gagal dibuat.", 500)
    _log(g.api_client, 201, "Order dibuat")
    return _json("Order berhasil dibuat dan masuk antrean proses.", 201, order={"invoice": invoice, "external_ref": external_ref, "status": order.order_status, "payment_status": order.payment_status, "amount": amount, "balance": int(g.api_client.balance or 0)})

@api_v1_bp.get("/order/<external_ref>")
@api_auth
def order_status(external_ref):
    api_order = ApiOrder.query.filter_by(client_id=g.api_client.id, external_ref=external_ref).first()
    if not api_order:
        _log(g.api_client, 404, "Order tidak ditemukan")
        return _json("Order tidak ditemukan.", 404)
    order = api_order.order
    _log(g.api_client, 200, "OK")
    return _json("Status order berhasil diambil.", order={"invoice": order.invoice, "external_ref": external_ref, "status": order.order_status, "payment_status": order.payment_status, "amount": api_order.charged_amount, "created_at": order.created_at.isoformat() if order.created_at else None})
