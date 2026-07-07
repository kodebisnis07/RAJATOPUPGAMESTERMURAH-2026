import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash, Response, current_app
from app.models import Category, CatalogSection, Product, Order, Banner, Promo, Testimonial, FAQ, Setting, PaymentMethod, Payment, UserNotification, User, Voucher, ResellerProfile
from app.extensions import db
from app.payments import create_payment
from app.utils import refund_wallet_order

home_bp = Blueprint("home", __name__)


def _notify_user(user_id, title, message, notif_type="info", order_id=None):
    if not user_id:
        return None
    notification = UserNotification(
        user_id=user_id,
        order_id=order_id,
        title=title,
        message=message,
        type=notif_type,
    )
    db.session.add(notification)
    return notification


def _expire_pending_orders():
    """Batalkan otomatis order pending yang belum dibayar setelah batas waktu pembayaran habis."""
    now = datetime.utcnow()
    expired = (
        Order.query
        .join(Payment, Payment.order_id == Order.id)
        .filter(
            Order.payment_status == "pending",
            Order.order_status == "pending",
            Payment.status == "pending",
            Payment.expired_at.isnot(None),
            Payment.expired_at <= now,
        )
        .all()
    )
    if not expired:
        return 0

    for order in expired:
        order.payment_status = "expired"
        order.order_status = "cancelled"
        order.cancelled_at = now
        if order.payment:
            order.payment.status = "expired"

        exists = UserNotification.query.filter_by(
            user_id=order.user_id,
            order_id=order.id,
            type="order_expired",
        ).first() if order.user_id else None
        if not exists:
            _notify_user(
                order.user_id,
                "Pesanan dibatalkan otomatis",
                f"Pesanan {order.invoice} dibatalkan karena belum dibayar dalam 10 menit.",
                "order_expired",
                order.id,
            )
    db.session.commit()
    return len(expired)


@home_bp.before_app_request
def auto_cancel_expired_orders():
    # Tidak membutuhkan scheduler eksternal; pengecekan berjalan otomatis setiap ada request website.
    try:
        _expire_pending_orders()
    except Exception:
        db.session.rollback()


def _login_required_redirect(next_endpoint=None, **values):
    """Redirect user biasa ke login sebelum bisa membuat/melihat pesanan."""
    if session.get("user_id"):
        return None
    flash("Silakan login terlebih dahulu sebelum melakukan top up.", "error")
    return redirect(url_for("auth.login"))



@home_bp.route("/robots.txt")
def robots_txt():
    # Izinkan Google meng-crawl halaman publik. Blokir area admin/login saja.
    base_url = current_app.config.get("SITE_URL", request.url_root.rstrip("/"))
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /super-admin\n"
        "Disallow: /auth\n"
        "Disallow: /login\n"
        "\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain; charset=utf-8")


@home_bp.route("/sitemap.xml")
def sitemap_xml():
    base_url = current_app.config.get("SITE_URL", request.url_root.rstrip("/"))
    urls = [
        ("/", "1.0"),
        ("/daftar", "0.6"),
        ("/login", "0.6"),
        ("/reseller", "0.5"),
    ]
    try:
        categories = Category.query.filter_by(status="active").order_by(Category.id.asc()).all()
        urls.extend([(url_for("home.topup", category_id=c.id), "0.9") for c in categories])
    except Exception:
        pass
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = datetime.utcnow().date().isoformat()
    for path, priority in urls:
        loc = path if path.startswith("http") else f"{base_url}{path}"
        xml.append(f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod><priority>{priority}</priority></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

@home_bp.route("/login")
def login_alias():
    return redirect(url_for("auth.login"))


@home_bp.route("/register", methods=["GET", "POST"])
@home_bp.route("/daftar", methods=["GET", "POST"])
def register_alias():
    # Jalankan langsung view register agar submit form dari /register atau /daftar
    # tidak mental ke beranda dan tidak kehilangan data POST.
    from app.routes.auth import register as auth_register_view
    return auth_register_view()


def _category_text(category):
    text_parts = [getattr(category, "name", "") or "", getattr(category, "slug", "") or ""]
    section = getattr(category, "catalog_section", None)
    if section:
        text_parts.extend([getattr(section, "title", "") or "", getattr(section, "slug", "") or ""])
    return " ".join(text_parts).lower()


def _category_input_config(category):
    """Atur form order sesuai jenis kategori tanpa menambah kolom database baru."""
    text = _category_text(category)
    if any(k in text for k in ["sosmed", "followers", "likes", "instagram", "tiktok", "facebook"]):
        return {
            "type": "social",
            "title": "Data Target Sosmed",
            "help": "Masukkan username atau link target sesuai layanan yang dipilih.",
            "label": "Username / Link Target",
            "placeholder": "Contoh: @username atau https://link-postingan",
            "needs_server": False,
            "required": True,
        }
    if any(k in text for k in ["netflix", "youtube", "disney", "hotstar", "iqiyi", "vidio", "capcut", "canva", "chatgpt", "gemini", "wetv", "aplikasi", "apps"]):
        return {
            "type": "account",
            "title": "Data Akun Aplikasi",
            "help": "Masukkan email, username, atau catatan akun yang dibutuhkan untuk proses aktivasi.",
            "label": "Email / Username",
            "placeholder": "Contoh: email@gmail.com",
            "needs_server": False,
            "required": True,
        }
    if any(k in text for k in ["telegram premium", "telegram stars", "stars"]):
        return {
            "type": "telegram",
            "title": "Data Akun Telegram",
            "help": "Masukkan username Telegram penerima layanan.",
            "label": "Username Telegram",
            "placeholder": "Contoh: @username",
            "needs_server": False,
            "required": True,
        }
    if any(k in text for k in ["pulsa", "telkomsel", "xl", "axis", "indosat", "tri", "smartfren"]):
        return {
            "type": "phone",
            "title": "Data Nomor Tujuan",
            "help": "Masukkan nomor HP tujuan pengisian pulsa.",
            "label": "Nomor HP",
            "placeholder": "Contoh: 081234567890",
            "needs_server": False,
            "required": True,
        }
    if any(k in text for k in ["e-wallet", "ewallet", "dana", "ovo", "gopay", "shopeepay", "linkaja"]):
        return {
            "type": "wallet",
            "title": "Data E-Wallet Tujuan",
            "help": "Masukkan nomor HP yang terdaftar di e-wallet tujuan.",
            "label": "Nomor E-Wallet",
            "placeholder": "Contoh: 081234567890",
            "needs_server": False,
            "required": True,
        }
    if any(k in text for k in ["voucher", "google play", "steam wallet", "garena shell", "gift card"]):
        return {
            "type": "voucher",
            "title": "Data Penerima Voucher",
            "help": "Masukkan email, nomor HP, atau catatan tujuan voucher.",
            "label": "Email / Nomor / Catatan",
            "placeholder": "Contoh: email@gmail.com atau 081234567890",
            "needs_server": False,
            "required": True,
        }
    return {
        "type": "game",
        "title": "Data Akun Game",
        "help": "Cukup isi User ID dan Zone/Server ID. Data pembeli otomatis memakai akun login Anda.",
        "label": "User ID",
        "placeholder": "Contoh: 123456789",
        "server_label": "Zone / Server ID",
        "server_placeholder": "Contoh: 1234",
        "needs_server": True,
        "required": True,
    }


def _category_requires_game_account(category):
    return _category_input_config(category).get("type") == "game"

@home_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", "").strip()
    section_id = request.args.get("section_id", "").strip()

    query = Category.query.filter_by(status="active")
    if q:
        query = query.filter(Category.name.ilike(f"%{q}%"))
    if category_id:
        try:
            query = query.filter(Category.id == int(category_id))
        except ValueError:
            category_id = ""
    if section_id:
        try:
            query = query.filter(Category.catalog_section_id == int(section_id))
        except ValueError:
            section_id = ""

    categories = Category.query.filter_by(status="active").order_by(Category.name.asc()).all()
    games = query.order_by(Category.sort_order.asc(), Category.name.asc()).all()
    catalog_sections = CatalogSection.query.filter_by(is_active=True).order_by(CatalogSection.sort_order.asc(), CatalogSection.title.asc()).all()
    def categories_for_section(slug):
        section = CatalogSection.query.filter_by(slug=slug, is_active=True).first()
        if not section:
            return []
        return Category.query.filter_by(status="active", catalog_section_id=section.id).order_by(Category.sort_order.asc(), Category.name.asc()).all()

    social_categories = categories_for_section("suntik-sosmed")
    voucher_categories = categories_for_section("voucher")
    pulsa_categories = categories_for_section("pulsa")
    ewallet_categories = categories_for_section("e-wallet")
    premium_categories = categories_for_section("aplikasi-premium")
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.sort_order.asc(), Banner.id.desc()).all()
    try:
        website_banners = json.loads((Setting.query.filter_by(key="website_banners_json").first().value or "[]") if Setting.query.filter_by(key="website_banners_json").first() else "[]")
    except Exception:
        website_banners = []
    website_banners = sorted([b for b in website_banners if b.get("is_active")], key=lambda x: (int(x.get("sort_order") or 0), str(x.get("id", ""))))
    promos = Promo.query.filter_by(is_active=True).order_by(Promo.id.desc()).limit(6).all()
    testimonials = Testimonial.query.filter_by(is_active=True).order_by(Testimonial.id.desc()).limit(6).all()
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.sort_order.asc(), FAQ.id.desc()).limit(8).all()
    settings = {item.key: item.value for item in Setting.query.all()}
    return render_template("index.html", games=games, categories=categories, catalog_sections=catalog_sections, social_categories=social_categories, voucher_categories=voucher_categories, pulsa_categories=pulsa_categories, ewallet_categories=ewallet_categories, premium_categories=premium_categories, banners=banners, website_banners=website_banners, promos=promos, testimonials=testimonials, faqs=faqs, settings=settings, q=q, selected_category=category_id, selected_section=section_id)


@home_bp.route("/topup/<int:category_id>", methods=["GET", "POST"])
def topup(category_id):
    login_redirect = _login_required_redirect()
    if login_redirect:
        return login_redirect

    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id, status="active").order_by(Product.price.asc()).all()
    settings = {item.key: item.value for item in Setting.query.all()}
    payment_methods = PaymentMethod.query.filter_by(is_active=True, is_offline=False).order_by(PaymentMethod.sort_order.asc(), PaymentMethod.name.asc()).all()

    input_config = _category_input_config(category)
    requires_game_account = input_config.get("type") == "game"
    current_user = User.query.get(session.get("user_id")) if session.get("user_id") else None

    if request.method == "POST":
        product_id = request.form.get("product_id")
        game_user_id = (request.form.get("game_user_id") or "").strip()
        game_server_id = (request.form.get("game_server_id") or "").strip() if input_config.get("needs_server") else None
        if input_config.get("required") and not game_user_id:
            flash(f"{input_config.get('label', 'Data target')} wajib diisi.", "error")
            return redirect(url_for("home.topup", category_id=category.id))
        customer_name = (current_user.name if current_user else None) or session.get("user_name")
        customer_email = (current_user.email if current_user else None) or session.get("user_email")
        customer_phone = (current_user.phone if current_user else None) or session.get("user_phone")
        voucher_code = (request.form.get("voucher_code") or "").strip().upper().replace(" ", "")
        voucher = Voucher.query.filter_by(code=voucher_code, is_active=True).first() if voucher_code else None
        payment_method_id = request.form.get("payment_method_id")
        use_wallet = payment_method_id == "saldo"
        selected_method = None
        if not use_wallet:
            selected_method = PaymentMethod.query.filter_by(id=payment_method_id, is_active=True, is_offline=False).first() if payment_method_id else None
            if not selected_method:
                flash("Metode pembayaran tidak tersedia atau sedang offline. Silakan pilih metode lain.", "error")
                return redirect(url_for("home.topup", category_id=category.id))

        product = Product.query.get_or_404(product_id)
        invoice = "INV" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        discount_amount = voucher.calculate_discount(product.price) if voucher else 0
        subtotal = max(0, product.price - discount_amount)
        admin_fee = 0 if use_wallet else (selected_method.admin_fee or 0)
        total_price = subtotal + admin_fee

        if use_wallet:
            if not current_user:
                flash("Silakan login terlebih dahulu untuk membayar memakai saldo.", "error")
                return redirect(url_for("auth.login"))
            if int(current_user.balance or 0) < total_price:
                flash(f"Saldo tidak cukup. Saldo Anda Rp {int(current_user.balance or 0):,}. Silakan top up saldo terlebih dahulu.", "error")
                return redirect(url_for("home.topup", category_id=category.id))
            payment_method = "Saldo RajaTopup"
            payment_reference = "WALLET"
            payment_status = "paid"
            order_status = "processing"
        else:
            payment_method = selected_method.name
            payment_reference = str(selected_method.id)
            payment_status = "pending"
            order_status = "pending"

        order = Order(
            invoice=invoice,
            user_id=session.get("user_id"),
            product_id=product.id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            game_user_id=game_user_id,
            game_server_id=game_server_id,
            price=total_price,
            voucher_code=voucher.code if voucher else None,
            discount_amount=discount_amount,
            payment_method=payment_method,
            payment_reference=payment_reference,
            payment_status=payment_status,
            order_status=order_status,
        )
        db.session.add(order)
        if voucher and discount_amount > 0:
            voucher.used_count = (voucher.used_count or 0) + 1
        db.session.commit()

        if use_wallet:
            current_user.balance = int(current_user.balance or 0) - total_price
            payment = Payment(
                order_id=order.id,
                payment_code="SALDO",
                payment_name="Saldo RajaTopup",
                provider="wallet",
                reference=invoice,
                amount=total_price,
                status="paid",
                paid_at=datetime.utcnow(),
            )
            db.session.add(payment)
            _notify_user(
                order.user_id,
                "Pembayaran saldo berhasil",
                f"Pesanan {order.invoice} berhasil dibayar memakai saldo dan sedang diproses.",
                "payment_paid",
                order.id,
            )
            flash("Pembayaran memakai saldo berhasil. Pesanan sedang diproses.", "success")
        else:
            create_payment(order)
            _notify_user(
                order.user_id,
                "Pesanan baru dibuat",
                f"Pesanan {order.invoice} berhasil dibuat. Silakan bayar dalam 10 menit agar pesanan tidak otomatis batal.",
                "order_created",
                order.id,
            )
        db.session.commit()
        return redirect(url_for("home.checkout", invoice=invoice))

    return render_template("topup.html", category=category, products=products, settings=settings, payment_methods=payment_methods, requires_game_account=requires_game_account, input_config=input_config, current_user=current_user)


@home_bp.route("/checkout/<invoice>")
def checkout(invoice):
    _expire_pending_orders()
    if not session.get("user_id"):
        flash("Silakan login dulu untuk melihat invoice pesanan.", "error")
        return redirect(url_for("auth.login"))

    order = Order.query.filter_by(invoice=invoice).first_or_404()
    if order.user_id != session.get("user_id"):
        flash("Invoice ini bukan milik akun Anda.", "error")
        return redirect(url_for("auth.dashboard"))

    settings = {item.key: item.value for item in Setting.query.all()}
    payment_method = None
    if order.payment_method:
        payment_method = PaymentMethod.query.filter_by(name=order.payment_method).first()
    return render_template("checkout.html", order=order, settings=settings, payment_method=payment_method)


@home_bp.route("/order/<invoice>/cancel", methods=["POST"])
def cancel_order(invoice):
    if not session.get("user_id"):
        flash("Silakan login dulu untuk membatalkan pesanan.", "error")
        return redirect(url_for("auth.login"))

    order = Order.query.filter_by(invoice=invoice, user_id=session.get("user_id")).first_or_404()

    if order.payment_status != "pending" or order.order_status != "pending":
        flash("Pesanan ini tidak bisa dibatalkan karena sudah diproses/dikonfirmasi admin atau status pembayaran berubah.", "error")
        return redirect(url_for("home.checkout", invoice=order.invoice))

    refunded_amount = refund_wallet_order(order, "Pesanan dibatalkan oleh user")
    order.payment_status = "cancelled"
    order.order_status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    if order.payment:
        order.payment.status = "cancelled"
    _notify_user(order.user_id, "Pesanan dibatalkan", f"Pesanan {order.invoice} berhasil Anda batalkan.", "order_cancelled", order.id)
    db.session.commit()
    if refunded_amount:
        flash(f"Pesanan berhasil dibatalkan. Saldo dikembalikan Rp {refunded_amount:,}.", "success")
    else:
        flash("Pesanan berhasil dibatalkan.", "success")
    return redirect(url_for("home.checkout", invoice=order.invoice))




@home_bp.route("/reseller", methods=["GET", "POST"])
def reseller_register():
    if not session.get("user_id"):
        flash("Silakan login terlebih dahulu untuk mendaftar reseller.", "error")
        return redirect(url_for("auth.login"))
    user_id = session.get("user_id")
    profile = ResellerProfile.query.filter_by(user_id=user_id).first()
    if request.method == "POST":
        if not profile:
            profile = ResellerProfile(user_id=user_id)
            db.session.add(profile)
        profile.store_name = (request.form.get("store_name") or "").strip()
        profile.note = (request.form.get("note") or "").strip()
        profile.status = "pending"
        db.session.commit()
        flash("Pendaftaran reseller berhasil dikirim. Admin akan memeriksa data Anda.", "success")
        return redirect(url_for("home.reseller_register"))
    return render_template("reseller.html", profile=profile)


@home_bp.route("/tripay/callback", methods=["POST"])
def tripay_callback():
    import hashlib
    import hmac
    from flask import current_app
    from app.models import Payment
    from app.utils import get_setting

    payload = request.get_json(silent=True) or {}
    private_key = get_setting("tripay_private_key")
    raw_body = request.get_data()
    callback_signature = request.headers.get("X-Callback-Signature", "")

    if private_key and callback_signature:
        expected = hmac.new(private_key.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, callback_signature):
            return jsonify({"success": False, "message": "Invalid signature"}), 403

    reference = payload.get("reference") or payload.get("merchant_ref")
    status = (payload.get("status") or "").upper()
    payment = Payment.query.filter((Payment.reference == reference) | (Payment.order.has(invoice=reference))).first() if reference else None

    if not payment:
        return jsonify({"success": False, "message": "Payment not found"}), 404

    if status in {"PAID", "SUCCESS"}:
        payment.status = "paid"
        payment.order.payment_status = "paid"
        payment.order.order_status = "processing"
        _notify_user(payment.order.user_id, "Pembayaran diterima", f"Pembayaran untuk pesanan {payment.order.invoice} sudah diterima dan sedang diproses.", "payment_paid", payment.order.id)
    elif status in {"EXPIRED", "FAILED", "CANCELLED"}:
        payment.status = status.lower()
        payment.order.payment_status = status.lower()
        payment.order.order_status = "failed"
        _notify_user(payment.order.user_id, "Pembayaran gagal/kedaluwarsa", f"Pembayaran untuk pesanan {payment.order.invoice} berstatus {status.lower()}.", "payment_failed", payment.order.id)
    db.session.commit()
    return jsonify({"success": True})
