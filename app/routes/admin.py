import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session, url_for, flash, current_app, jsonify, abort
from app.extensions import db
from app.models import Admin, Category, CatalogSection, Product, Order, User, Payment, PaymentMethod, Setting, Banner, Promo, Testimonial, FAQ, FavoriteGame, AdminActivityLog, WalletTopup, UserNotification, ChatThread, ChatMessage, Voucher, ResellerProfile
from app.utils import unique_slug, save_uploaded_image, set_setting, get_setting, refund_wallet_order

def _clean_prefix(value, fallback):
    value = (value or fallback).strip()
    if not value.startswith("/"):
        value = "/" + value
    return value.rstrip("/") or fallback


# URL panel dibuat tetap agar tidak berubah karena ENV Render yang salah/kosong.
ADMIN_PANEL_PATH = "/panel-rtg-2026-X7q9K"
SUPER_ADMIN_PANEL_PATH = "/super-panel-rtg-2026-S9kL2"

admin_bp = Blueprint("admin", __name__, url_prefix=ADMIN_PANEL_PATH)
super_admin_bp = Blueprint("super_admin", __name__, url_prefix=SUPER_ADMIN_PANEL_PATH)


def current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    return Admin.query.get(admin_id)


def admin_required():
    admin = current_admin()
    return bool(admin and admin.is_active)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not admin_required():
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        admin = current_admin()
        if not admin or not admin.is_active:
            return redirect(url_for("super_admin.login"))
        if admin.role != "super_admin":
            flash("Hanya Super Admin yang bisa membuka menu ini.", "error")
            return redirect(url_for("admin.dashboard"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*allowed_roles):
    """Batasi halaman admin berdasarkan role.

    Role yang dipakai:
    - super_admin: akses penuh
    - admin: kelola konten/produk/setting, tetapi tidak kelola akun admin lain
    - operator: fokus operasional pesanan, user, dan pembayaran
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            admin = current_admin()
            if not admin or not admin.is_active:
                return redirect(url_for("admin.login"))
            if admin.role == "super_admin":
                return view(*args, **kwargs)
            if admin.role not in allowed_roles:
                flash("Akses ditolak. Role Anda tidak diizinkan membuka menu ini.", "error")
                return redirect(url_for("admin.dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator



def _money(value):
    return int(value or 0)


def _paid_orders_query():
    return Order.query.filter(Order.payment_status == "paid")


def _sum_paid_between(start_dt, end_dt):
    return _money(
        db.session.query(db.func.sum(Order.price))
        .filter(Order.payment_status == "paid", Order.created_at >= start_dt, Order.created_at < end_dt)
        .scalar()
    )


def _count_paid_between(start_dt, end_dt):
    return (
        Order.query
        .filter(Order.payment_status == "paid", Order.created_at >= start_dt, Order.created_at < end_dt)
        .count()
    )


def _month_start(dt=None):
    dt = dt or datetime.utcnow()
    return datetime(dt.year, dt.month, 1)


def _next_month_start(dt=None):
    start = _month_start(dt)
    if start.month == 12:
        return datetime(start.year + 1, 1, 1)
    return datetime(start.year, start.month + 1, 1)


def _add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    return datetime(year, month, 1)


def _omset_summary():
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    tomorrow_start = today_start + timedelta(days=1)
    this_month_start = _month_start(now)
    next_month_start = _next_month_start(now)
    last_month_start = _add_months(this_month_start, -1)

    return {
        "today_income": _sum_paid_between(today_start, tomorrow_start),
        "today_count": _count_paid_between(today_start, tomorrow_start),
        "month_income": _sum_paid_between(this_month_start, next_month_start),
        "month_count": _count_paid_between(this_month_start, next_month_start),
        "last_month_income": _sum_paid_between(last_month_start, this_month_start),
        "last_month_count": _count_paid_between(last_month_start, this_month_start),
        "total_income": _money(db.session.query(db.func.sum(Order.price)).filter(Order.payment_status == "paid").scalar()),
        "total_count": Order.query.filter_by(payment_status="paid").count(),
    }


def _monthly_omset_history(months=12):
    now = datetime.utcnow()
    current = _month_start(now)
    rows = []
    for index in range(months):
        start = _add_months(current, -index)
        end = _add_months(start, 1)
        rows.append({
            "label": start.strftime("%B %Y"),
            "month": start.month,
            "year": start.year,
            "start": start,
            "end": end,
            "income": _sum_paid_between(start, end),
            "count": _count_paid_between(start, end),
        })
    return rows


def _daily_omset_history(days=31):
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    rows = []
    for index in range(days):
        start = today - timedelta(days=index)
        end = start + timedelta(days=1)
        rows.append({
            "label": start.strftime("%d-%m-%Y"),
            "income": _sum_paid_between(start, end),
            "count": _count_paid_between(start, end),
        })
    return rows


def role_permission_key(role, permission):
    return f"role_permission:{role}:{permission}"


def get_role_permission(role, permission, default=False):
    value = get_setting(role_permission_key(role, permission), "1" if default else "0")
    return str(value).lower() in ["1", "true", "yes", "on", "aktif"]


def set_role_permission(role, permission, enabled):
    set_setting(role_permission_key(role, permission), "1" if enabled else "0")


def can_reset_user_password():
    admin = current_admin()
    if not admin or not admin.is_active:
        return False
    if admin.role == "super_admin":
        return True
    return get_role_permission(admin.role, "reset_user_password", False)


def is_operator():
    admin = current_admin()
    return bool(admin and admin.role == "operator")


def _game_upload_folder():
    folder = os.path.join(current_app.root_path, "static", "img", "games")
    os.makedirs(folder, exist_ok=True)
    return folder


def _delete_game_image(filename):
    if not filename:
        return
    path = os.path.join(_game_upload_folder(), filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _payment_upload_folder():
    folder = os.path.join(current_app.root_path, "static", "img", "payment_methods")
    os.makedirs(folder, exist_ok=True)
    return folder


def _delete_payment_image(filename):
    if not filename:
        return
    path = os.path.join(_payment_upload_folder(), filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@admin_bp.app_context_processor
def inject_admin_context():
    admin = current_admin()
    return {
        "current_admin": admin,
        "is_super_admin": bool(admin and admin.role == "super_admin"),
        "is_admin_role": bool(admin and admin.role in ["super_admin", "admin"]),
        "is_operator": bool(admin and admin.role == "operator"),
        "can_reset_user_password": can_reset_user_password(),
    }


@admin_bp.route("/")
def index():
    return redirect(url_for("admin.dashboard" if admin_required() else "admin.login"))


def _start_admin_session(admin):
    session.clear()
    session["admin_id"] = admin.id
    session["admin_username"] = admin.username
    session["admin_role"] = admin.role


def log_admin_activity(action, description=""):
    """Catat semua aktivitas penting admin/operator agar bisa dipantau Super Admin."""
    admin = current_admin()
    try:
        log = AdminActivityLog(
            admin_id=admin.id if admin else None,
            admin_username=admin.username if admin else session.get("admin_username"),
            admin_role=admin.role if admin else session.get("admin_role"),
            action=action,
            description=description,
            ip_address=(request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr),
            user_agent=(request.headers.get("User-Agent", "")[:255]),
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login Admin/Operator. Super Admin juga boleh login lewat link ini.

    Setelah login, semua akses tetap dibatasi oleh role di backend.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.is_active and admin.check_password(password):
            _start_admin_session(admin)
            log_admin_activity("login", f"{admin.role} login melalui panel admin rahasia")
            flash(f"Berhasil login sebagai {admin.role}.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/login.html", error="Username atau password salah / akun nonaktif", portal="admin")
    return render_template("admin/login.html", portal="admin")


@super_admin_bp.route("/")
def super_index():
    admin = current_admin()
    if admin and admin.is_active and admin.role == "super_admin":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("super_admin.login"))


@super_admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login khusus Super Admin."""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.is_active and admin.check_password(password):
            if admin.role != "super_admin":
                return render_template(
                    "admin/login.html",
                    error="Akun Admin/Operator harus login melalui link Admin.",
                    portal="super_admin",
                )
            _start_admin_session(admin)
            log_admin_activity("login", "Super Admin login melalui panel super admin rahasia")
            flash("Berhasil login sebagai Super Admin.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/login.html", error="Username atau password salah / akun nonaktif", portal="super_admin")
    return render_template("admin/login.html", portal="super_admin")


@super_admin_bp.route("/logout")
def logout():
    log_admin_activity("logout", "Super Admin logout")
    session.clear()
    flash("Super Admin berhasil logout.", "success")
    return redirect(url_for("super_admin.login"))


@super_admin_bp.route("/change-password")
@super_admin_required
def change_password():
    return redirect(url_for("admin.super_admin_change_password"))



# Endpoint lama sengaja diblokir agar panel tidak mudah ditebak.
# Panel aktif ada di ADMIN_PANEL_PATH, default: /panel-rtg-2026-X7q9K
def register_legacy_admin_blockers(app):
    @app.route("/admin")
    @app.route("/admin/")
    @app.route("/admin/<path:_path>")
    @app.route("/super-admin")
    @app.route("/super-admin/")
    @app.route("/super-admin/<path:_path>")
    def _legacy_admin_blocked(_path=None):
        abort(404)


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_orders = Order.query.count()
    total_admins = Admin.query.count()
    total_users = User.query.count()
    omset = _omset_summary()
    total_income = omset["total_income"]
    pending_orders = Order.query.filter_by(payment_status="pending").count()
    paid_orders = Order.query.filter_by(payment_status="paid").count()
    failed_orders = Order.query.filter(Order.payment_status.in_(["failed", "expired", "cancelled"])) .count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
    best_products = (
        db.session.query(Product.name, db.func.count(Order.id).label("total"), db.func.sum(Order.price).label("income"))
        .join(Order, Order.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(db.desc("total"))
        .limit(5)
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_categories=total_categories,
        total_orders=total_orders,
        total_admins=total_admins,
        total_users=total_users,
        total_income=total_income,
        pending_orders=pending_orders,
        paid_orders=paid_orders,
        failed_orders=failed_orders,
        recent_orders=recent_orders,
        best_products=best_products,
        omset=omset,
        monthly_history=_monthly_omset_history(6),
    )


@admin_bp.route("/omset")
@super_admin_required
def omset():
    """Halaman riwayat omset Super Admin.

    Omset bulanan tidak disimpan sebagai angka statis, tetapi dihitung dari
    pesanan berstatus paid berdasarkan tanggal created_at. Karena itu setiap
    awal bulan Omset Bulan Ini otomatis kembali ke 0, sedangkan bulan lama
    tetap tampil sebagai riwayat.
    """
    return render_template(
        "admin/omset.html",
        omset=_omset_summary(),
        monthly_history=_monthly_omset_history(24),
        daily_history=_daily_omset_history(31),
    )


@super_admin_bp.route("/omset")
@super_admin_required
def omset_redirect():
    return redirect(url_for("admin.omset"))


@admin_bp.route("/categories", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def categories():
    sections = CatalogSection.query.order_by(CatalogSection.sort_order.asc(), CatalogSection.title.asc()).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        status = request.form.get("status", "active")
        section_id = request.form.get("catalog_section_id") or None
        badge = request.form.get("badge", "").strip() or None
        sort_order = int(request.form.get("sort_order") or 0)
        is_featured = bool(request.form.get("is_featured"))
        if not name:
            flash("Nama game wajib diisi.", "error")
            return redirect(url_for("admin.categories"))
        if Category.query.filter_by(name=name).first():
            flash("Nama game/kategori sudah ada.", "error")
            return redirect(url_for("admin.categories"))
        try:
            icon_name = save_uploaded_image(request.files.get("icon"), _game_upload_folder())
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.categories"))
        db.session.add(Category(name=name, slug=unique_slug(Category, name), icon=icon_name, catalog_section_id=section_id, badge=badge, sort_order=sort_order, is_featured=is_featured, status=status))
        db.session.commit()
        log_admin_activity("tambah_kategori", f"Menambahkan kategori/game: {name}")
        flash("Kategori/game berhasil ditambahkan.", "success")
        return redirect(url_for("admin.categories"))
    categories = Category.query.order_by(Category.sort_order.asc(), Category.name.asc()).all()
    return render_template("admin/categories.html", categories=categories, sections=sections)


@admin_bp.route("/categories/<int:id>/edit", methods=["POST"])
@role_required("super_admin", "admin")
def edit_category(id):
    category = Category.query.get_or_404(id)
    name = request.form.get("name", "").strip()
    if name:
        category.name = name
        category.slug = unique_slug(Category, name, current_id=category.id)
    category.status = request.form.get("status", category.status)
    category.catalog_section_id = request.form.get("catalog_section_id") or None
    category.badge = request.form.get("badge", "").strip() or None
    category.sort_order = int(request.form.get("sort_order") or 0)
    category.is_featured = bool(request.form.get("is_featured"))
    try:
        icon_name = save_uploaded_image(request.files.get("icon"), _game_upload_folder())
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.categories"))
    if icon_name:
        _delete_game_image(category.icon)
        category.icon = icon_name
    if request.form.get("remove_icon") == "1":
        _delete_game_image(category.icon)
        category.icon = None
    db.session.commit()
    log_admin_activity("edit_kategori", f"Memperbarui kategori/game ID {category.id}: {category.name}")
    flash("Kategori/game berhasil diperbarui.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/delete/<int:id>")
@role_required("super_admin", "admin")
def delete_category(id):
    category = Category.query.get_or_404(id)
    _delete_game_image(category.icon)
    deleted_name = category.name
    db.session.delete(category)
    db.session.commit()
    log_admin_activity("hapus_kategori", f"Menghapus kategori/game: {deleted_name}")
    flash("Kategori berhasil dihapus.", "success")
    return redirect(url_for("admin.categories"))


def _save_product_from_form(product=None):
    name = request.form.get("name", "").strip()
    price = int(request.form.get("price") or 0)
    price_modal = int(request.form.get("price_modal") or 0)
    stock = int(request.form.get("stock") or 0)
    category_id = int(request.form.get("category_id") or 0)
    status = request.form.get("status") or "active"
    description = request.form.get("description") or ""
    provider = request.form.get("provider") or ""
    provider_code = request.form.get("provider_code") or ""
    if not name or not price or not category_id:
        raise ValueError("Nama, harga, dan kategori/game wajib diisi.")
    try:
        image_name = save_uploaded_image(request.files.get("image"), current_app.config["UPLOAD_FOLDER"])
    except ValueError as exc:
        raise exc
    if product is None:
        product = Product(name=name, slug=unique_slug(Product, name))
        db.session.add(product)
    else:
        product.name = name
        product.slug = unique_slug(Product, name, current_id=product.id)
    product.price = price
    product.price_modal = price_modal
    product.stock = stock
    product.category_id = category_id
    product.status = status
    product.description = description
    product.provider = provider
    product.provider_code = provider_code
    if image_name:
        if product.image:
            old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], product.image)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        product.image = image_name
    return product


@admin_bp.route("/products", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def products():
    categories = Category.query.order_by(Category.name.asc()).all()
    if request.method == "POST":
        try:
            _save_product_from_form()
            db.session.commit()
            log_admin_activity("tambah_produk", "Menambahkan produk/nominal baru")
            flash("Produk berhasil ditambahkan.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.products"))
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/products.html", products=products, categories=categories)


@admin_bp.route("/nominals", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def nominals():
    """Menu khusus nominal/paket. Secara database tetap memakai tabel products."""
    categories = Category.query.order_by(Category.name.asc()).all()
    selected_category = request.args.get("category_id", "")
    if request.method == "POST":
        try:
            _save_product_from_form()
            db.session.commit()
            log_admin_activity("tambah_nominal", "Menambahkan nominal/paket baru")
            flash("Nominal berhasil ditambahkan.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.nominals"))
    query = Product.query
    if selected_category:
        try:
            query = query.filter(Product.category_id == int(selected_category))
        except ValueError:
            selected_category = ""
    products = query.order_by(Product.category_id.asc(), Product.price.asc()).all()
    return render_template("admin/nominals.html", products=products, categories=categories, selected_category=selected_category)


@admin_bp.route("/products/<int:id>/edit", methods=["POST"])
@role_required("super_admin", "admin")
def edit_product(id):
    product = Product.query.get_or_404(id)
    try:
        _save_product_from_form(product)
        db.session.commit()
        log_admin_activity("edit_produk", f"Memperbarui produk ID {product.id}: {product.name}")
        flash("Produk berhasil diperbarui.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    target = request.form.get("next") or url_for("admin.products")
    return redirect(target)


@admin_bp.route("/products/delete/<int:id>", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def delete_product(id):
    product = Product.query.get_or_404(id)
    if product.image:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], product.image)
        if os.path.exists(path):
            os.remove(path)
    deleted_name = product.name
    db.session.delete(product)
    db.session.commit()
    log_admin_activity("hapus_produk", f"Menghapus produk: {deleted_name}")
    flash("Produk berhasil dihapus.", "success")
    return redirect(request.referrer or url_for("admin.products"))


@admin_bp.route("/catalog-sections", methods=["GET", "POST"])
@super_admin_required
def catalog_sections():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subtitle = request.form.get("subtitle", "").strip()
        sort_order = int(request.form.get("sort_order") or 0)
        is_active = bool(request.form.get("is_active"))
        if not title:
            flash("Nama section wajib diisi.", "error")
            return redirect(url_for("admin.catalog_sections"))
        section = CatalogSection(title=title, slug=unique_slug(CatalogSection, title), subtitle=subtitle, sort_order=sort_order, is_active=is_active)
        db.session.add(section)
        db.session.commit()
        flash("Section katalog berhasil ditambahkan.", "success")
        return redirect(url_for("admin.catalog_sections"))
    sections = CatalogSection.query.order_by(CatalogSection.sort_order.asc(), CatalogSection.id.desc()).all()
    unassigned_count = Category.query.filter(Category.catalog_section_id.is_(None)).count()
    return render_template("admin/catalog_sections.html", sections=sections, unassigned_count=unassigned_count)


@admin_bp.route("/catalog-sections/<int:id>/update", methods=["POST"])
@super_admin_required
def update_catalog_section(id):
    section = CatalogSection.query.get_or_404(id)
    title = request.form.get("title", "").strip()
    if title:
        section.title = title
        section.slug = unique_slug(CatalogSection, title, current_id=section.id)
    section.subtitle = request.form.get("subtitle", "").strip()
    section.sort_order = int(request.form.get("sort_order") or 0)
    section.is_active = bool(request.form.get("is_active"))
    db.session.commit()
    flash("Section katalog berhasil diperbarui.", "success")
    return redirect(url_for("admin.catalog_sections"))


@admin_bp.route("/catalog-sections/<int:id>/delete", methods=["POST"])
@super_admin_required
def delete_catalog_section(id):
    section = CatalogSection.query.get_or_404(id)
    Category.query.filter_by(catalog_section_id=section.id).update({"catalog_section_id": None})
    db.session.delete(section)
    db.session.commit()
    flash("Section katalog dihapus. Game yang sebelumnya berada di section ini menjadi belum dikelompokkan.", "success")
    return redirect(url_for("admin.catalog_sections"))


@admin_bp.route("/slide-banners", methods=["GET", "POST"])
@super_admin_required
def slide_banners():
    # Slide Banner khusus untuk hero slider besar di bagian paling atas homepage.
    if request.method == "POST":
        try:
            image_name = save_uploaded_image(request.files.get("image"), current_app.config["UPLOAD_FOLDER"])
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.slide_banners"))
        banner = Banner(
            title=request.form.get("title", "").strip(),
            subtitle=request.form.get("subtitle", ""),
            tag=request.form.get("tag", "RAJA TOPUP GAMES").strip() or "RAJA TOPUP GAMES",
            image=image_name,
            button_text=request.form.get("button_text", "Top Up Sekarang"),
            link=request.form.get("link", "#games"),
            sort_order=int(request.form.get("sort_order") or 0),
            is_active=bool(request.form.get("is_active")),
        )
        if banner.title:
            db.session.add(banner)
            db.session.commit()
            flash("Slide banner berhasil ditambahkan.", "success")
        return redirect(url_for("admin.slide_banners"))
    banners = Banner.query.order_by(Banner.sort_order.asc(), Banner.id.desc()).all()
    return render_template("admin/slide_banners.html", banners=banners)


def _load_website_banners():
    raw = get_setting("website_banners_json", "[]")
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_website_banners(items):
    set_setting("website_banners_json", json.dumps(items, ensure_ascii=False))
    db.session.commit()


# =========================
# BANNER WEBSITE / PROMO CARD
# =========================
# Route ini sengaja dibuat banyak alias supaya menu Banner Website TIDAK lagi nyasar
# ke halaman Slide Banner. Semua URL di bawah akan membuka template website_banners.html.
@admin_bp.route("/website-banners", methods=["GET", "POST"])
@admin_bp.route("/website-banner", methods=["GET", "POST"])
@admin_bp.route("/banner-website", methods=["GET", "POST"])
@admin_bp.route("/banners-website", methods=["GET", "POST"])
@admin_bp.route("/promo-banners", methods=["GET", "POST"])
@admin_bp.route("/banners", methods=["GET", "POST"])  # kompatibilitas link lama: sekarang masuk Banner Website
@super_admin_bp.route("/website-banners", methods=["GET", "POST"])
@super_admin_bp.route("/website-banner", methods=["GET", "POST"])
@super_admin_bp.route("/banner-website", methods=["GET", "POST"])
@super_admin_bp.route("/banners-website", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def website_banners():
    # Banner Website berbeda dari Slide Banner. Ini tampil sebagai kartu promo khusus di homepage.
    items = _load_website_banners()
    if request.method == "POST":
        try:
            image_name = save_uploaded_image(request.files.get("image"), current_app.config["UPLOAD_FOLDER"])
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.website_banners"))
        item = {
            "id": datetime.utcnow().strftime("%Y%m%d%H%M%S%f"),
            "title": request.form.get("title", "").strip(),
            "subtitle": request.form.get("subtitle", ""),
            "badge": request.form.get("badge", "PROMO WEBSITE").strip() or "PROMO WEBSITE",
            "image": image_name,
            "button_text": request.form.get("button_text", "Lihat Promo"),
            "link": request.form.get("link", "#games"),
            "sort_order": int(request.form.get("sort_order") or 0),
            "is_active": bool(request.form.get("is_active")),
        }
        if item["title"]:
            items.append(item)
            _save_website_banners(items)
            flash("Banner website berhasil ditambahkan dan akan tampil di blok promo homepage.", "success")
        return redirect(url_for("admin.website_banners"))
    items = sorted(items, key=lambda x: (int(x.get("sort_order") or 0), str(x.get("id", ""))))
    return render_template("admin/website_banners.html", banners=items)


@admin_bp.route("/banners/<int:id>/update", methods=["POST"])
@role_required("super_admin", "admin")
def update_banner(id):
    banner = Banner.query.get_or_404(id)
    banner.title = request.form.get("title", "").strip() or banner.title
    banner.subtitle = request.form.get("subtitle", "")
    banner.tag = request.form.get("tag", "RAJA TOPUP GAMES").strip() or "RAJA TOPUP GAMES"
    banner.button_text = request.form.get("button_text", "Top Up Sekarang")
    banner.link = request.form.get("link", "#games")
    banner.sort_order = int(request.form.get("sort_order") or 0)
    banner.is_active = bool(request.form.get("is_active"))
    try:
        new_image = save_uploaded_image(request.files.get("image"), current_app.config["UPLOAD_FOLDER"])
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.slide_banners"))
    if new_image:
        banner.image = new_image
    db.session.commit()
    flash("Banner berhasil diperbarui.", "success")
    return redirect(url_for("admin.slide_banners"))


@admin_bp.route("/banners/<int:id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_banner(id):
    db.session.delete(Banner.query.get_or_404(id))
    db.session.commit()
    flash("Banner berhasil dihapus.", "success")
    return redirect(url_for("admin.slide_banners"))


@admin_bp.route("/website-banners/<banner_id>/update", methods=["POST"])
@super_admin_bp.route("/website-banners/<banner_id>/update", methods=["POST"])
@role_required("super_admin", "admin")
def update_website_banner(banner_id):
    items = _load_website_banners()
    for item in items:
        if str(item.get("id")) == str(banner_id):
            item["title"] = request.form.get("title", "").strip() or item.get("title", "")
            item["subtitle"] = request.form.get("subtitle", "")
            item["badge"] = request.form.get("badge", "PROMO WEBSITE").strip() or "PROMO WEBSITE"
            item["button_text"] = request.form.get("button_text", "Lihat Promo")
            item["link"] = request.form.get("link", "#games")
            item["sort_order"] = int(request.form.get("sort_order") or 0)
            item["is_active"] = bool(request.form.get("is_active"))
            try:
                new_image = save_uploaded_image(request.files.get("image"), current_app.config["UPLOAD_FOLDER"])
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("admin.website_banners"))
            if new_image:
                item["image"] = new_image
            _save_website_banners(items)
            flash("Banner website berhasil diperbarui.", "success")
            break
    return redirect(url_for("admin.website_banners"))


@admin_bp.route("/website-banners/<banner_id>/delete", methods=["POST"])
@super_admin_bp.route("/website-banners/<banner_id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_website_banner(banner_id):
    items = [item for item in _load_website_banners() if str(item.get("id")) != str(banner_id)]
    _save_website_banners(items)
    flash("Banner website berhasil dihapus.", "success")
    return redirect(url_for("admin.website_banners"))


@admin_bp.route("/promos", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def promos():
    if request.method == "POST":
        promo = Promo(title=request.form.get("title", "").strip(), description=request.form.get("description", ""), badge=request.form.get("badge", "PROMO"), link=request.form.get("link", ""), is_active=bool(request.form.get("is_active")))
        if promo.title:
            db.session.add(promo)
            db.session.commit()
            flash("Promo berhasil ditambahkan.", "success")
        return redirect(url_for("admin.promos"))
    promos = Promo.query.order_by(Promo.id.desc()).all()
    return render_template("admin/promos.html", promos=promos)


@admin_bp.route("/promos/<int:id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_promo(id):
    db.session.delete(Promo.query.get_or_404(id))
    db.session.commit()
    flash("Promo berhasil dihapus.", "success")
    return redirect(url_for("admin.promos"))




@admin_bp.route("/vouchers", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def vouchers():
    if request.method == "POST":
        code = (request.form.get("code") or "").strip().upper().replace(" ", "")
        title = (request.form.get("title") or "").strip() or code
        if not code:
            flash("Kode voucher wajib diisi.", "error")
            return redirect(url_for("admin.vouchers"))
        item = Voucher.query.filter_by(code=code).first() or Voucher(code=code, title=title)
        item.title = title
        item.discount_type = request.form.get("discount_type") or "fixed"
        item.discount_value = int(request.form.get("discount_value") or 0)
        item.min_order = int(request.form.get("min_order") or 0)
        item.quota = int(request.form.get("quota") or 0)
        item.is_active = bool(request.form.get("is_active"))
        db.session.add(item)
        db.session.commit()
        flash("Voucher berhasil disimpan.", "success")
        return redirect(url_for("admin.vouchers"))
    vouchers = Voucher.query.order_by(Voucher.id.desc()).all()
    return render_template("admin/vouchers.html", vouchers=vouchers)


@admin_bp.route("/vouchers/<int:id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_voucher(id):
    db.session.delete(Voucher.query.get_or_404(id))
    db.session.commit()
    flash("Voucher berhasil dihapus.", "success")
    return redirect(url_for("admin.vouchers"))


@admin_bp.route("/resellers")
@role_required("super_admin", "admin")
def resellers():
    items = ResellerProfile.query.order_by(ResellerProfile.id.desc()).all()
    return render_template("admin/resellers.html", items=items)


@admin_bp.route("/resellers/<int:id>/update", methods=["POST"])
@role_required("super_admin", "admin")
def update_reseller(id):
    item = ResellerProfile.query.get_or_404(id)
    item.status = request.form.get("status", item.status)
    item.level = request.form.get("level", item.level)
    item.commission_percent = int(request.form.get("commission_percent") or 0)
    item.note = request.form.get("note", "")
    db.session.commit()
    flash("Status reseller berhasil diperbarui.", "success")
    return redirect(url_for("admin.resellers"))


@admin_bp.route("/testimonials", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def testimonials():
    if request.method == "POST":
        item = Testimonial(name=request.form.get("name", "").strip(), message=request.form.get("message", "").strip(), rating=int(request.form.get("rating") or 5), is_active=bool(request.form.get("is_active")))
        if item.name and item.message:
            db.session.add(item)
            db.session.commit()
            flash("Testimoni berhasil ditambahkan.", "success")
        return redirect(url_for("admin.testimonials"))
    testimonials = Testimonial.query.order_by(Testimonial.id.desc()).all()
    return render_template("admin/testimonials.html", testimonials=testimonials)


@admin_bp.route("/testimonials/<int:id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_testimonial(id):
    db.session.delete(Testimonial.query.get_or_404(id))
    db.session.commit()
    flash("Testimoni berhasil dihapus.", "success")
    return redirect(url_for("admin.testimonials"))


@admin_bp.route("/faqs", methods=["GET", "POST"])
@role_required("super_admin", "admin")
def faqs():
    if request.method == "POST":
        item = FAQ(question=request.form.get("question", "").strip(), answer=request.form.get("answer", "").strip(), sort_order=int(request.form.get("sort_order") or 0), is_active=bool(request.form.get("is_active")))
        if item.question and item.answer:
            db.session.add(item)
            db.session.commit()
            flash("FAQ berhasil ditambahkan.", "success")
        return redirect(url_for("admin.faqs"))
    faqs = FAQ.query.order_by(FAQ.sort_order.asc(), FAQ.id.desc()).all()
    return render_template("admin/faqs.html", faqs=faqs)


@admin_bp.route("/faqs/<int:id>/delete", methods=["POST"])
@role_required("super_admin", "admin")
def delete_faq(id):
    db.session.delete(FAQ.query.get_or_404(id))
    db.session.commit()
    flash("FAQ berhasil dihapus.", "success")
    return redirect(url_for("admin.faqs"))


@admin_bp.route("/orders")
@login_required
def orders():
    return render_template("admin/orders.html", orders=Order.query.order_by(Order.id.desc()).all())


@admin_bp.route("/orders/<int:id>/update", methods=["POST"])
@login_required
def update_order(id):
    order = Order.query.get_or_404(id)
    allowed_payment_statuses = ["pending", "paid", "cancelled", "failed", "expired"]
    allowed_order_statuses = ["pending", "processing", "success", "completed", "cancelled", "failed"]

    old_payment_status = order.payment_status
    old_order_status = order.order_status

    payment_status = request.form.get("payment_status", order.payment_status)
    order_status = request.form.get("order_status", order.order_status)

    if payment_status not in allowed_payment_statuses:
        payment_status = order.payment_status
    if order_status not in allowed_order_statuses:
        order_status = order.order_status

    will_be_cancelled = payment_status in ["cancelled", "failed", "expired"] or order_status in ["cancelled", "failed"]
    was_already_cancelled = old_payment_status in ["cancelled", "failed", "expired"] or old_order_status in ["cancelled", "failed"]

    refunded_amount = 0
    if will_be_cancelled and not was_already_cancelled:
        refunded_amount = refund_wallet_order(order, "Status pesanan dibatalkan oleh admin")
        if not order.cancelled_at:
            order.cancelled_at = datetime.utcnow()

    order.payment_status = payment_status
    order.order_status = order_status

    if order.payment:
        order.payment.status = payment_status

    db.session.commit()
    log_admin_activity("ubah_status_order", f"Mengubah {order.invoice}: pembayaran={payment_status}, order={order_status}, refund_saldo={refunded_amount}")
    if refunded_amount:
        flash(f"Status pesanan {order.invoice} berhasil diperbarui. Saldo user dikembalikan Rp {refunded_amount:,}.", "success")
    else:
        flash(f"Status pesanan {order.invoice} berhasil diperbarui.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/users")
@login_required
def users():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    query = User.query
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(User.name.ilike(like), User.username.ilike(like), User.email.ilike(like), User.phone.ilike(like)))
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))

    users = query.order_by(User.id.desc()).all()
    user_stats = {}
    for user in users:
        orders = Order.query.filter_by(user_id=user.id).all()
        user_stats[user.id] = {
            "total_orders": len(orders),
            "paid_orders": sum(1 for order in orders if order.payment_status == "paid"),
            "pending_orders": sum(1 for order in orders if order.payment_status == "pending"),
            "cancelled_orders": sum(1 for order in orders if order.order_status == "cancelled" or order.payment_status == "cancelled"),
            "total_spend": sum(order.price or 0 for order in orders if order.payment_status == "paid"),
        }
    return render_template("admin/users.html", users=users, user_stats=user_stats, search=search, status=status)


@admin_bp.route("/users/<int:id>")
@super_admin_required
def user_detail(id):
    user = User.query.get_or_404(id)
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
    favorites = FavoriteGame.query.filter_by(user_id=user.id).order_by(FavoriteGame.id.desc()).all()
    stats = {
        "total_orders": len(orders),
        "paid_orders": sum(1 for order in orders if order.payment_status == "paid"),
        "pending_orders": sum(1 for order in orders if order.payment_status == "pending"),
        "cancelled_orders": sum(1 for order in orders if order.order_status == "cancelled" or order.payment_status == "cancelled"),
        "total_spend": sum(order.price or 0 for order in orders if order.payment_status == "paid"),
    }
    return render_template("admin/user_detail.html", user=user, orders=orders, favorites=favorites, stats=stats)


@admin_bp.route("/users/<int:id>/update", methods=["POST"])
@super_admin_required
def update_user(id):
    user = User.query.get_or_404(id)
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip().lower()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    member_level = request.form.get("member_level", user.member_level or "Bronze")

    if not name or not username or not email:
        flash("Nama, username, dan email wajib diisi.", "error")
        return redirect(url_for("admin.user_detail", id=user.id))
    if not (4 <= len(username) <= 30) or not all(ch.isalnum() or ch in "._-" for ch in username):
        flash("Username harus 4-30 karakter dan hanya boleh memakai huruf, angka, titik, garis bawah, atau strip.", "error")
        return redirect(url_for("admin.user_detail", id=user.id))
    duplicate_username = User.query.filter(User.username == username, User.id != user.id).first()
    if duplicate_username:
        flash("Username sudah digunakan user lain.", "error")
        return redirect(url_for("admin.user_detail", id=user.id))
    duplicate_email = User.query.filter(User.email == email, User.id != user.id).first()
    if duplicate_email:
        flash("Email sudah digunakan user lain.", "error")
        return redirect(url_for("admin.user_detail", id=user.id))
    if phone:
        duplicate_phone = User.query.filter(User.phone == phone, User.id != user.id).first()
        if duplicate_phone:
            flash("Nomor telepon sudah digunakan user lain.", "error")
            return redirect(url_for("admin.user_detail", id=user.id))

    user.name = name
    user.username = username
    user.email = email
    user.phone = phone or None
    user.member_level = member_level
    user.role = request.form.get("role", user.role or "user")
    user.is_active = bool(request.form.get("is_active"))
    db.session.commit()
    log_admin_activity("edit_user", f"Memperbarui data user ID {user.id}: {user.username or user.email}")
    flash("Data user berhasil diperbarui.", "success")
    return redirect(url_for("admin.user_detail", id=user.id))


@admin_bp.route("/users/<int:id>/reset-password", methods=["POST"])
@login_required
def reset_user_password(id):
    if not can_reset_user_password():
        flash("Akses ditolak. Role Anda tidak diizinkan mereset password user.", "error")
        return redirect(url_for("admin.users"))
    user = User.query.get_or_404(id)
    new_password = request.form.get("new_password", "").strip()
    if len(new_password) < 6:
        flash("Password baru minimal 6 karakter.", "error")
        return redirect(url_for("admin.user_detail", id=user.id))
    user.set_password(new_password)
    db.session.commit()
    log_admin_activity("reset_password_user", f"Reset password user ID {user.id}: {user.username or user.email}")
    flash("Password user berhasil direset. Berikan password baru ini langsung kepada user secara aman.", "success")
    return redirect(url_for("admin.user_detail", id=user.id))


@admin_bp.route("/users/<int:id>/toggle", methods=["POST"])
@super_admin_required
def toggle_user(id):
    user = User.query.get_or_404(id)
    user.is_active = not bool(user.is_active)
    db.session.commit()
    log_admin_activity("ubah_status_user", f"Mengubah status aktif user ID {user.id}: {user.username or user.email}")
    flash("Status akun user berhasil diubah.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@admin_bp.route("/users/<int:id>/delete", methods=["POST"])
@super_admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    Order.query.filter_by(user_id=user.id).update({"user_id": None})
    FavoriteGame.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    log_admin_activity("hapus_user", f"Menghapus user ID {id}")
    flash("User berhasil dihapus. Riwayat pesanan tetap disimpan tanpa akun user.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/role-permissions", methods=["GET", "POST"])
@super_admin_required
def role_permissions():
    """Super Admin mengatur izin khusus untuk role admin dan operator."""
    roles = ["admin", "operator"]
    permissions = {
        "reset_user_password": "Reset password user",
    }
    if request.method == "POST":
        for role in roles:
            for permission in permissions:
                enabled = request.form.get(f"{role}_{permission}") == "1"
                set_role_permission(role, permission, enabled)
        db.session.commit()
        log_admin_activity("ubah_izin_role", "Memperbarui izin role admin/operator")
        flash("Izin role Admin dan Operator berhasil diperbarui.", "success")
        return redirect(url_for("admin.role_permissions"))

    current_permissions = {
        role: {permission: get_role_permission(role, permission, False) for permission in permissions}
        for role in roles
    }
    return render_template(
        "admin/role_permissions.html",
        roles=roles,
        permissions=permissions,
        current_permissions=current_permissions,
    )


@admin_bp.route("/admins", methods=["GET", "POST"])
@super_admin_required
def admins():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "admin")
        is_active = bool(request.form.get("is_active"))
        if not username or not password:
            flash("Username dan password wajib diisi.", "error")
            return redirect(url_for("admin.admins"))
        if len(password) < 6:
            flash("Password admin/operator minimal 6 karakter.", "error")
            return redirect(url_for("admin.admins"))
        if role not in ["super_admin", "admin", "operator"]:
            role = "admin"
        if Admin.query.filter_by(username=username).first():
            flash("Username admin sudah digunakan.", "error")
            return redirect(url_for("admin.admins"))
        new_admin = Admin(username=username, name=name or username, role=role, is_active=is_active)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        log_admin_activity("tambah_admin", f"Menambahkan akun {role}: {username}")
        flash("Admin baru berhasil ditambahkan.", "success")
        return redirect(url_for("admin.admins"))
    return render_template("admin/admins.html", admins=Admin.query.order_by(Admin.id.asc()).all())


@admin_bp.route("/admins/<int:id>/update", methods=["POST"])
@super_admin_required
def update_admin(id):
    admin = Admin.query.get_or_404(id)
    admin.name = request.form.get("name", "").strip() or admin.username
    role = request.form.get("role", admin.role)
    # Hindari Super Admin terkunci sendiri dari panel.
    if admin.id == session.get("admin_id") and admin.role == "super_admin" and role != "super_admin":
        flash("Anda tidak bisa menurunkan role akun Super Admin yang sedang dipakai.", "error")
        return redirect(url_for("admin.admins"))
    if role in ["super_admin", "admin", "operator"]:
        admin.role = role
    if admin.id == session.get("admin_id") and admin.role == "super_admin" and not request.form.get("is_active"):
        flash("Akun Super Admin yang sedang login tidak bisa dinonaktifkan.", "error")
        return redirect(url_for("admin.admins"))
    admin.is_active = bool(request.form.get("is_active"))
    new_password = request.form.get("password", "").strip()
    if new_password:
        if len(new_password) < 6:
            flash("Password baru minimal 6 karakter.", "error")
            return redirect(url_for("admin.admins"))
        admin.set_password(new_password)
    db.session.commit()
    log_admin_activity("edit_admin", f"Memperbarui akun admin/operator ID {admin.id}: {admin.username}")
    flash("Data admin berhasil diperbarui.", "success")
    return redirect(url_for("admin.admins"))


@admin_bp.route("/admins/<int:id>/delete", methods=["POST"])
@super_admin_required
def delete_admin(id):
    admin = Admin.query.get_or_404(id)
    if admin.id == session.get("admin_id"):
        flash("Akun yang sedang login tidak bisa dihapus.", "error")
        return redirect(url_for("admin.admins"))
    deleted_username = admin.username
    db.session.delete(admin)
    db.session.commit()
    log_admin_activity("hapus_admin", f"Menghapus akun admin/operator: {deleted_username}")
    flash("Admin berhasil dihapus.", "success")
    return redirect(url_for("admin.admins"))


@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Admin, Operator, dan Super Admin mengganti password akunnya sendiri."""
    admin = current_admin()
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not admin.check_password(current_password):
            flash("Password lama tidak sesuai.", "error")
            return redirect(url_for("admin.change_password"))
        if len(new_password) < 6:
            flash("Password baru minimal 6 karakter.", "error")
            return redirect(url_for("admin.change_password"))
        if new_password != confirm_password:
            flash("Konfirmasi password baru tidak sama.", "error")
            return redirect(url_for("admin.change_password"))

        admin.set_password(new_password)
        db.session.commit()
        log_admin_activity("ganti_password_sendiri", f"{admin.role} {admin.username} mengganti password akunnya sendiri")
        flash("Password berhasil diganti. Gunakan password baru saat login berikutnya.", "success")
        return redirect(url_for("admin.change_password"))

    return render_template("admin/change_password.html")


@admin_bp.route("/super-admin/change-password", methods=["GET", "POST"])
@super_admin_required
def super_admin_change_password():
    """Alias lama agar link /admin/super-admin/change-password tetap aman dan mengarah ke fitur yang sama."""
    return change_password()


@admin_bp.route("/payment-methods", methods=["GET", "POST"])
@super_admin_required
def payment_methods():
    if request.method == "POST":
        try:
            logo_name = save_uploaded_image(request.files.get("logo"), _payment_upload_folder())
            qr_name = save_uploaded_image(request.files.get("qr_image"), _payment_upload_folder())
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.payment_methods"))

        method = PaymentMethod(
            name=request.form.get("name", "").strip(),
            type=request.form.get("type", "bank"),
            account_number=request.form.get("account_number", "").strip(),
            account_name=request.form.get("account_name", "").strip(),
            logo=logo_name,
            qr_image=qr_name,
            instruction=request.form.get("instruction", "").strip(),
            admin_fee=int(request.form.get("admin_fee") or 0),
            sort_order=int(request.form.get("sort_order") or 0),
            is_active=bool(request.form.get("is_active")),
            is_offline=bool(request.form.get("is_offline")),
        )
        if not method.name:
            flash("Nama metode pembayaran wajib diisi.", "error")
            return redirect(url_for("admin.payment_methods"))
        db.session.add(method)
        db.session.commit()
        log_admin_activity("tambah_metode_pembayaran", f"Menambahkan metode pembayaran: {method.name}")
        flash("Metode pembayaran berhasil ditambahkan.", "success")
        return redirect(url_for("admin.payment_methods"))

    methods = PaymentMethod.query.order_by(PaymentMethod.sort_order.asc(), PaymentMethod.id.desc()).all()
    return render_template("admin/payment_methods.html", methods=methods)


@admin_bp.route("/payment-methods/<int:id>/edit", methods=["POST"])
@super_admin_required
def edit_payment_method(id):
    method = PaymentMethod.query.get_or_404(id)
    try:
        logo_name = save_uploaded_image(request.files.get("logo"), _payment_upload_folder())
        qr_name = save_uploaded_image(request.files.get("qr_image"), _payment_upload_folder())
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.payment_methods"))

    method.name = request.form.get("name", "").strip() or method.name
    method.type = request.form.get("type", method.type)
    method.account_number = request.form.get("account_number", "").strip()
    method.account_name = request.form.get("account_name", "").strip()
    method.instruction = request.form.get("instruction", "").strip()
    method.admin_fee = int(request.form.get("admin_fee") or 0)
    method.sort_order = int(request.form.get("sort_order") or 0)
    method.is_active = bool(request.form.get("is_active"))
    method.is_offline = bool(request.form.get("is_offline"))

    if logo_name:
        _delete_payment_image(method.logo)
        method.logo = logo_name
    if qr_name:
        _delete_payment_image(method.qr_image)
        method.qr_image = qr_name
    if request.form.get("remove_logo") == "1":
        _delete_payment_image(method.logo)
        method.logo = None
    if request.form.get("remove_qr") == "1":
        _delete_payment_image(method.qr_image)
        method.qr_image = None

    db.session.commit()
    log_admin_activity("edit_metode_pembayaran", f"Memperbarui metode pembayaran: {method.name}")
    flash("Metode pembayaran berhasil diperbarui.", "success")
    return redirect(url_for("admin.payment_methods"))


@admin_bp.route("/payment-methods/<int:id>/toggle", methods=["POST"])
@super_admin_required
def toggle_payment_method(id):
    method = PaymentMethod.query.get_or_404(id)
    action = request.form.get("action")
    if action == "offline":
        method.is_offline = True
        flash(f"{method.name} sekarang OFFLINE.", "success")
    elif action == "online":
        method.is_offline = False
        method.is_active = True
        flash(f"{method.name} sekarang ONLINE dan aktif.", "success")
    elif action == "deactivate":
        method.is_active = False
        flash(f"{method.name} dinonaktifkan.", "success")
    elif action == "activate":
        method.is_active = True
        method.is_offline = False
        flash(f"{method.name} diaktifkan.", "success")
    db.session.commit()
    log_admin_activity("ubah_status_metode_pembayaran", f"Mengubah status metode pembayaran: {method.name}")
    return redirect(url_for("admin.payment_methods"))


@admin_bp.route("/payment-methods/<int:id>/delete", methods=["POST"])
@super_admin_required
def delete_payment_method(id):
    method = PaymentMethod.query.get_or_404(id)
    _delete_payment_image(method.logo)
    _delete_payment_image(method.qr_image)
    deleted_name = method.name
    db.session.delete(method)
    db.session.commit()
    log_admin_activity("hapus_metode_pembayaran", f"Menghapus metode pembayaran: {deleted_name}")
    flash("Metode pembayaran berhasil dihapus.", "success")
    return redirect(url_for("admin.payment_methods"))


@admin_bp.route("/auto-order", methods=["GET", "POST"])
@super_admin_required
def auto_order():
    """Panel konsep/kontrol Auto Order khusus Super Admin.

    Fitur ini menyiapkan menu dan pengaturan dasar untuk integrasi otomatis.
    Integrasi nyata ke Tripay/Midtrans/Xendit dan Digiflazz/VIP/APIGames
    perlu ditambahkan pada tahap API/webhook berikutnya.
    """
    keys = [
        "auto_order_enabled",
        "auto_order_mode",
        "auto_order_retry",
        "auto_order_callback_url",
        "auto_order_webhook_secret",
        "topup_provider",
        "topup_provider_status",
        "topup_username",
        "topup_api_key",
        "topup_private_key",
        "topup_callback_url",
        "payment_auto_verify",
        "payment_gateway_provider",
        "payment_gateway_status",
        "payment_merchant_code",
        "payment_api_key",
        "payment_private_key",
        "payment_webhook_url",
    ]
    if request.method == "POST":
        for key in keys:
            set_setting(key, request.form.get(key, ""))
        db.session.commit()
        log_admin_activity("ubah_auto_order", "Memperbarui pengaturan Auto Order")
        flash("Pengaturan Auto Order berhasil disimpan. Menu sudah siap untuk tahap integrasi API/webhook.", "success")
        return redirect(url_for("admin.auto_order"))

    settings = {item.key: item.value for item in Setting.query.all()}
    status_summary = {
        "pending_payment": Order.query.filter_by(payment_status="pending").count(),
        "paid": Order.query.filter_by(payment_status="paid").count(),
        "processing": Order.query.filter_by(order_status="processing").count(),
        "success": Order.query.filter(db.or_(Order.order_status == "success", Order.order_status == "completed")).count(),
        "failed": Order.query.filter_by(order_status="failed").count(),
        "cancelled": Order.query.filter(db.or_(Order.order_status == "cancelled", Order.payment_status == "cancelled")).count(),
    }
    recent_orders = Order.query.order_by(Order.id.desc()).limit(10).all()
    return render_template("admin/auto_order.html", settings=settings, status_summary=status_summary, recent_orders=recent_orders)


@admin_bp.route("/audit-log")
@super_admin_required
def audit_log():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "").strip()
    action = request.args.get("action", "").strip()
    query = AdminActivityLog.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(AdminActivityLog.admin_username.ilike(like), AdminActivityLog.description.ilike(like), AdminActivityLog.ip_address.ilike(like)))
    if role:
        query = query.filter(AdminActivityLog.admin_role == role)
    if action:
        query = query.filter(AdminActivityLog.action == action)
    logs = query.order_by(AdminActivityLog.id.desc()).limit(300).all()
    actions = [row[0] for row in db.session.query(AdminActivityLog.action).distinct().order_by(AdminActivityLog.action.asc()).all()]
    return render_template("admin/audit_log.html", logs=logs, q=q, role=role, action=action, actions=actions)


@admin_bp.route("/wallet-topups")
@login_required
def wallet_topups():
    status = request.args.get("status", "").strip()
    query = WalletTopup.query
    if status:
        query = query.filter_by(status=status)
    topups = query.order_by(WalletTopup.created_at.desc()).all()
    return render_template("admin/wallet_topups.html", topups=topups, status=status)


@admin_bp.route("/wallet-topups/<int:id>/update", methods=["POST"])
@login_required
def update_wallet_topup(id):
    trx = WalletTopup.query.get_or_404(id)
    action = request.form.get("action")
    note = request.form.get("note", "").strip()

    if trx.status != "pending":
        flash("Top up saldo sudah diproses sebelumnya.", "error")
        return redirect(url_for("admin.wallet_topups"))

    if action == "approve":
        trx.status = "approved"
        trx.approved_at = datetime.utcnow()
        trx.note = note
        trx.user.balance = int(trx.user.balance or 0) + int(trx.amount or 0)
        trx.user.bonus_coins = int(trx.user.bonus_coins or 0) + int(trx.bonus_coins or 0)
        db.session.add(UserNotification(
            user_id=trx.user_id,
            title="Top up saldo berhasil",
            message=f"Saldo Rp {trx.amount:,} sudah masuk. Bonus koin +{trx.bonus_coins} juga sudah ditambahkan.",
            type="wallet_approved",
        ))
        log_admin_activity("approve_topup_saldo", f"Approve top up saldo {trx.invoice} user {trx.user.username if trx.user else trx.user_id}")
        flash("Top up saldo berhasil disetujui dan saldo user sudah ditambahkan.", "success")
    elif action == "reject":
        trx.status = "rejected"
        trx.note = note
        db.session.add(UserNotification(
            user_id=trx.user_id,
            title="Top up saldo ditolak",
            message=f"Top up saldo {trx.invoice} ditolak. {note}",
            type="wallet_rejected",
        ))
        log_admin_activity("reject_topup_saldo", f"Menolak top up saldo {trx.invoice}")
        flash("Top up saldo ditolak.", "success")
    else:
        flash("Aksi tidak valid.", "error")
        return redirect(url_for("admin.wallet_topups"))

    db.session.commit()
    return redirect(url_for("admin.wallet_topups"))

@admin_bp.route("/payments")
@login_required
def payments():
    return render_template("admin/payments.html", payments=Payment.query.order_by(Payment.id.desc()).all())


@admin_bp.route("/seo", methods=["GET", "POST"])
@role_required("admin")
def seo_settings():
    if request.method == "POST":
        keys = [
            "meta_title", "meta_description", "meta_keywords",
            "google_site_verification", "google_analytics_id", "facebook_pixel_id"
        ]
        for key in keys:
            set_setting(key, request.form.get(key, ""))
        db.session.commit()
        log_admin_activity("ubah_seo", "Memperbarui pengaturan SEO website")
        flash("Pengaturan SEO berhasil disimpan.", "success")
        return redirect(url_for("admin.seo_settings"))
    settings = {item.key: item.value for item in Setting.query.all()}
    return render_template("admin/seo.html", settings=settings)


@admin_bp.route("/settings", methods=["GET", "POST"])
@super_admin_required
def settings():
    if request.method == "POST":
        keys = [
            "site_name", "site_tagline", "whatsapp", "telegram", "instagram",
            "meta_title", "meta_description", "meta_keywords", "google_site_verification",
            "google_analytics_id", "facebook_pixel_id",
            "payment_gateway", "tripay_mode", "tripay_api_key", "tripay_private_key",
            "tripay_merchant_code", "duitku_merchant_code", "duitku_api_key", "xendit_secret_key"
        ]
        for key in keys:
            set_setting(key, request.form.get(key, ""))
        db.session.commit()
        log_admin_activity("ubah_pengaturan", "Memperbarui pengaturan website/payment gateway")
        flash("Pengaturan berhasil disimpan.", "success")
        return redirect(url_for("admin.settings"))
    settings = {item.key: item.value for item in Setting.query.all()}
    return render_template("admin/settings.html", settings=settings)


@admin_bp.route("/logout")
def logout():
    log_admin_activity("logout", "Admin/operator logout")
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/live-chat", methods=["GET", "POST"])
@login_required
def live_chat():
    admin = current_admin()
    selected_thread_id = request.args.get("thread_id", type=int)
    selected_thread = None

    if request.method == "POST":
        selected_thread_id = request.form.get("thread_id", type=int)
        message = (request.form.get("message") or "").strip()
        selected_thread = ChatThread.query.get_or_404(selected_thread_id)
        if not message:
            flash("Balasan tidak boleh kosong.", "error")
            return redirect(url_for("admin.live_chat", thread_id=selected_thread.id))
        db.session.add(ChatMessage(
            thread_id=selected_thread.id,
            sender_type=admin.role,
            sender_id=admin.id,
            sender_name=admin.name or admin.username,
            message=message,
            is_read_by_user=False,
            is_read_by_admin=True,
        ))
        selected_thread.status = "open"
        selected_thread.last_message_at = datetime.utcnow()
        db.session.commit()
        log_admin_activity("reply_chat", f"Membalas live chat user #{selected_thread.user_id}")
        return redirect(url_for("admin.live_chat", thread_id=selected_thread.id))

    threads = ChatThread.query.order_by(ChatThread.last_message_at.desc(), ChatThread.created_at.desc()).limit(100).all()
    if selected_thread_id:
        selected_thread = ChatThread.query.get(selected_thread_id)
    elif threads:
        selected_thread = threads[0]

    messages = []
    if selected_thread:
        unread_user_messages = ChatMessage.query.filter_by(thread_id=selected_thread.id, sender_type="user", is_read_by_admin=False).all()
        for msg in unread_user_messages:
            msg.is_read_by_admin = True
        if unread_user_messages:
            db.session.commit()
        messages = ChatMessage.query.filter_by(thread_id=selected_thread.id).order_by(ChatMessage.created_at.asc()).all()

    return render_template("admin/live_chat.html", threads=threads, selected_thread=selected_thread, messages=messages)


@admin_bp.route("/live-chat/<int:thread_id>/close", methods=["POST"])
@login_required
def close_live_chat(thread_id):
    thread = ChatThread.query.get_or_404(thread_id)
    thread.status = "closed"
    db.session.commit()
    log_admin_activity("close_chat", f"Menutup live chat user #{thread.user_id}")
    flash("Live chat ditutup.", "success")
    return redirect(url_for("admin.live_chat", thread_id=thread.id))
