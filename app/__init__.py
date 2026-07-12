import os
import sqlite3
from flask import Flask, send_from_directory, render_template, request, abort
from config import Config
from app.extensions import db, migrate
from sqlalchemy import inspect, text


def ensure_sqlite_columns(app):
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri.startswith("sqlite:///"):
        return
    db_path = db_uri.replace("sqlite:///", "", 1)
    if not os.path.exists(db_path):
        return
    columns = {
        "admins": {"name": "VARCHAR(120)", "role": "VARCHAR(30) DEFAULT 'admin'", "is_active": "BOOLEAN DEFAULT 1"},
        "categories": {"icon": "VARCHAR(500)", "catalog_section_id": "INTEGER", "badge": "VARCHAR(60)", "sort_order": "INTEGER DEFAULT 0", "is_featured": "BOOLEAN DEFAULT 1"},
        "users": {"username": "VARCHAR(80)", "phone": "VARCHAR(30)", "avatar": "VARCHAR(500)", "member_level": "VARCHAR(30) DEFAULT 'Bronze'", "balance": "INTEGER DEFAULT 0", "bonus_coins": "INTEGER DEFAULT 0"},
        "products": {"image": "VARCHAR(500)", "price_modal": "INTEGER DEFAULT 0", "provider": "VARCHAR(100)", "provider_code": "VARCHAR(100)", "stock": "INTEGER DEFAULT 0", "game_id": "INTEGER"},
        "orders": {"payment_url": "VARCHAR(500)", "payment_reference": "VARCHAR(150)", "cancelled_at": "DATETIME", "voucher_code": "VARCHAR(60)", "discount_amount": "INTEGER DEFAULT 0"},
        "payments": {
            "provider": "VARCHAR(50)",
            "reference": "VARCHAR(150)",
            "checkout_url": "VARCHAR(500)",
            "qr_url": "VARCHAR(500)",
        },
        "banners": {"tag": "VARCHAR(80) DEFAULT 'RAJA TOPUP GAMES'"},
    }
    conn = sqlite3.connect(db_path)
    try:
        for table, missing_columns in columns.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for column, col_type in missing_columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

        # Isi username untuk user lama agar tetap bisa login memakai username.
        existing = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if "username" in existing:
            rows = conn.execute("SELECT id, name, email, username FROM users").fetchall()
            used = {str(r[3]).lower() for r in rows if r[3]}
            for user_id, name, email, username in rows:
                if username:
                    continue
                base = (email.split('@')[0] if email and '@' in email else (name or f'user{user_id}')).lower()
                base = ''.join(ch for ch in base if ch.isalnum() or ch in '._-').strip('._-') or f'user{user_id}'
                candidate = base[:60]
                counter = 1
                while candidate.lower() in used:
                    counter += 1
                    candidate = f"{base[:55]}{counter}"
                used.add(candidate.lower())
                conn.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, user_id))

        existing_sections_table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_sections'").fetchone()
        if existing_sections_table:
            count = conn.execute("SELECT COUNT(*) FROM catalog_sections").fetchone()[0]
            if count == 0:
                conn.execute(
                    "INSERT INTO catalog_sections (title, slug, subtitle, sort_order, is_active, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                    ("Game Populer", "game-populer", "Pilih game, lalu lanjutkan ke halaman top up.", 1, 1),
                )
                default_id = conn.execute("SELECT id FROM catalog_sections WHERE slug = ?", ("game-populer",)).fetchone()[0]
                cat_cols = {row[1] for row in conn.execute("PRAGMA table_info(categories)")}
                if "catalog_section_id" in cat_cols:
                    conn.execute("UPDATE categories SET catalog_section_id = ? WHERE catalog_section_id IS NULL", (default_id,))
        conn.commit()
    finally:
        conn.close()



def ensure_runtime_columns(app):
    """Tambahkan kolom penting untuk database lama (SQLite/PostgreSQL) tanpa menghapus data."""
    try:
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name
        existing_tables = set(inspector.get_table_names())
        if "orders" not in existing_tables:
            return
        order_columns = {col["name"] for col in inspector.get_columns("orders")}
        user_columns = {col["name"] for col in inspector.get_columns("users")} if "users" in existing_tables else set()
        banner_columns = {col["name"] for col in inspector.get_columns("banners")} if "banners" in existing_tables else set()
        ddl_statements = []
        if "cancelled_at" not in order_columns:
            if dialect == "postgresql":
                ddl_statements.append("ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP")
            else:
                ddl_statements.append("ALTER TABLE orders ADD COLUMN cancelled_at DATETIME")
        if "voucher_code" not in order_columns:
            ddl_statements.append("ALTER TABLE orders ADD COLUMN voucher_code VARCHAR(60)")
        if "discount_amount" not in order_columns:
            ddl_statements.append("ALTER TABLE orders ADD COLUMN discount_amount INTEGER DEFAULT 0")
        if "balance" not in user_columns:
            ddl_statements.append("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0")
        if "bonus_coins" not in user_columns:
            ddl_statements.append("ALTER TABLE users ADD COLUMN bonus_coins INTEGER DEFAULT 0")
        if "banners" in existing_tables and "tag" not in banner_columns:
            ddl_statements.append("ALTER TABLE banners ADD COLUMN tag VARCHAR(80) DEFAULT 'RAJA TOPUP GAMES'")

        # Cloudinary URLs are longer than the old local filenames.
        if dialect == "postgresql":
            media_columns = {
                "users": ["avatar"],
                "categories": ["icon"],
                "games": ["image"],
                "products": ["image"],
                "payment_methods": ["logo", "qr_image"],
                "banners": ["image"],
            }
            for table, columns in media_columns.items():
                if table not in existing_tables:
                    continue
                column_info = {col["name"]: col for col in inspector.get_columns(table)}
                for column in columns:
                    info = column_info.get(column)
                    current_length = getattr(info.get("type"), "length", None) if info else None
                    if info and current_length and current_length < 500:
                        ddl_statements.append(
                            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(500)"
                        )
        with db.engine.begin() as conn:
            for ddl in ddl_statements:
                conn.execute(text(ddl))
    except Exception:
        # Jangan hentikan aplikasi jika migrasi ringan gagal; tabel baru tetap dibuat oleh db.create_all().
        pass

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.setdefault("UPLOAD_FOLDER", os.path.join(app.root_path, "static", "img", "products"))
    app.config.setdefault("AVATAR_UPLOAD_FOLDER", os.path.join(app.root_path, "static", "img", "avatars"))
    app.config.setdefault("SITE_ASSET_UPLOAD_FOLDER", os.path.join(app.root_path, "static", "img", "site"))

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models

    from app.routes.home import home_bp
    from app.routes.admin import admin_bp, super_admin_bp, register_legacy_admin_blockers
    from app.routes.auth import auth_bp
    from app.routes.api_v1 import api_v1_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(super_admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_v1_bp)
    register_legacy_admin_blockers(app)

    from app.admin_path import (
        DynamicAdminPathMiddleware,
        INTERNAL_ADMIN_PATH,
        INTERNAL_SUPER_ADMIN_PATH,
        DEFAULT_ADMIN_PATH,
        DEFAULT_SUPER_ADMIN_PATH,
        normalize_panel_path,
    )
    app.wsgi_app = DynamicAdminPathMiddleware(app, app.wsgi_app)

    @app.before_request
    def block_inactive_internal_admin_paths():
        if request.environ.get("RTG_BLOCK_INTERNAL_ADMIN_PATH") == "1":
            abort(404)

    @app.after_request
    def expose_dynamic_admin_urls(response):
        admin_public = request.environ.get("RTG_ADMIN_PUBLIC_PATH", DEFAULT_ADMIN_PATH)
        super_public = request.environ.get("RTG_SUPER_ADMIN_PUBLIC_PATH", DEFAULT_SUPER_ADMIN_PATH)

        location = response.headers.get("Location")
        if location:
            location = location.replace(INTERNAL_SUPER_ADMIN_PATH, super_public)
            location = location.replace(INTERNAL_ADMIN_PATH, admin_public)
            response.headers["Location"] = location

        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type and not response.direct_passthrough:
            try:
                html = response.get_data(as_text=True)
                changed = html.replace(INTERNAL_SUPER_ADMIN_PATH, super_public)
                changed = changed.replace(INTERNAL_ADMIN_PATH, admin_public)
                if changed != html:
                    response.set_data(changed)
                    response.headers["Content-Length"] = str(len(response.get_data()))
            except Exception:
                pass
        return response


    @app.route("/manifest.webmanifest")
    def manifest():
        return send_from_directory(
            app.static_folder,
            "manifest.webmanifest",
            mimetype="application/manifest+json"
        )

    @app.route("/service-worker.js")
    def service_worker():
        return send_from_directory(
            app.static_folder,
            "service-worker.js",
            mimetype="application/javascript"
        )

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.route("/google0b480b200ce87ddb.html")
    def google_search_console_verification():
        return send_from_directory(
            app.static_folder,
            "google0b480b200ce87ddb.html",
            mimetype="text/html"
        )
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


    @app.after_request
    def prevent_auth_cache(response):
        # Form login/daftar tidak boleh di-cache browser/service worker.
        try:
            from flask import request
            if request.path.startswith('/auth') or request.path in ('/daftar', '/register'):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            if request.path == '/service-worker.js':
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            if request.path.startswith(('/static/img/products/', '/static/img/games/', '/static/img/avatars/', '/static/img/payment_methods/', '/static/img/site/')):
                response.headers['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        except Exception:
            pass

        # Header keamanan dasar untuk production.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        return response

    @app.context_processor
    def inject_media_helpers():
        from app.utils import media_url, build_image_url
        return {"media_url": media_url, "image_url": build_image_url}

    @app.context_processor
    def inject_seo_context():
        # Setting global agar title/meta/OG tetap tersedia di semua halaman.
        from flask import request
        try:
            from app.models import Setting
            settings = {item.key: item.value for item in Setting.query.all()}
        except Exception:
            settings = {}
        base_url = app.config.get("SITE_URL", request.url_root.rstrip("/"))
        return {
            "global_settings": settings,
            "site_url": base_url,
            "canonical_url": base_url + request.path,
        }

    @app.context_processor
    def inject_user_context():
        from flask import session
        from app.models import UserNotification, User
        user_id = session.get("user_id")
        unread_notifications_count = 0
        current_user = None
        if user_id:
            try:
                current_user = User.query.get(user_id)
            except Exception:
                current_user = None
            try:
                unread_notifications_count = UserNotification.query.filter_by(user_id=user_id, is_read=False).count()
            except Exception:
                unread_notifications_count = 0
        return {
            "unread_notifications_count": unread_notifications_count,
            "current_user": current_user,
        }

    from app.cli import register_cli
    register_cli(app)

    with app.app_context():
        db.create_all()
        ensure_sqlite_columns(app)
        ensure_runtime_columns(app)
        db.create_all()
        from app.seed import seed_initial_data
        seed_initial_data()

    return app