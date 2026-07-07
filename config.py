import os
from datetime import timedelta


def _database_uri():
    """Ambil database dari Render/hosting. Fallback lokal tetap SQLite."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        # Render kadang memberi postgres://, sedangkan SQLAlchemy baru butuh postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    return "sqlite:///" + os.path.join(base_dir, "rajatopup.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "rajatopup-dev-secret-change-me")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Upload
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # Session production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Website/SEO defaults, bisa dioverride lewat tabel settings/panel admin.
    SITE_NAME = os.environ.get("SITE_NAME", "Raja Topup Games")
    SITE_URL = os.environ.get("SITE_URL", "https://rajatopupgames-termurah2026.onrender.com").rstrip("/")
    DEFAULT_META_DESCRIPTION = os.environ.get(
        "DEFAULT_META_DESCRIPTION",
        "Top up game murah, cepat, aman, dan terpercaya 24 jam."
    )


    # Link panel admin rahasia.
    # Ubah ADMIN_PANEL_PATH di Render Environment jika ingin link lain.
    # Jangan gunakan /admin agar tidak mudah ditebak bot/orang umum.
    ADMIN_PANEL_PATH = os.environ.get("ADMIN_PANEL_PATH", "/panel-rtg-2026-X7q9K").strip() or "/panel-rtg-2026-X7q9K"
    SUPER_ADMIN_PANEL_PATH = os.environ.get("SUPER_ADMIN_PANEL_PATH", "/super-panel-rtg-2026-S9kL2").strip() or "/super-panel-rtg-2026-S9kL2"

    # Email reset password. Jika belum diisi, link reset akan dicatat di log aplikasi.
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "noreply@localhost")

    # Telegram notification optional
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
