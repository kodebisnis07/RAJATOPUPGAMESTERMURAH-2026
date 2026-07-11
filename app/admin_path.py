"""Dynamic public URLs for the admin panels.

Flask blueprints keep stable internal prefixes. This middleware maps configurable
public prefixes to those internal routes, then response rewriting keeps links,
forms, and redirects on the configured public URL.
"""
import re
import time

INTERNAL_ADMIN_PATH = "/panel-rtg-2026-X7q9K"
INTERNAL_SUPER_ADMIN_PATH = "/super-panel-rtg-2026-S9kL2"
DEFAULT_ADMIN_PATH = INTERNAL_ADMIN_PATH
DEFAULT_SUPER_ADMIN_PATH = INTERNAL_SUPER_ADMIN_PATH

_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,63}$")
RESERVED_SLUGS = {
    "admin", "super-admin", "auth", "api", "api-v1", "static", "healthz",
    "login", "register", "daftar", "logout", "manifest.webmanifest",
    "service-worker.js",
}


def normalize_panel_path(value, fallback):
    value = (value or "").strip().strip("/")
    if not value:
        return fallback
    return "/" + value


def validate_panel_slug(value):
    slug = (value or "").strip().strip("/")
    if not _SLUG_RE.fullmatch(slug):
        return None, "Link panel harus 8–64 karakter dan hanya boleh berisi huruf, angka, atau tanda minus (-)."
    if slug.lower() in RESERVED_SLUGS:
        return None, "Link tersebut tidak boleh digunakan karena termasuk alamat sistem."
    return slug, None


class DynamicAdminPathMiddleware:
    def __init__(self, flask_app, wsgi_app, cache_seconds=3):
        self.flask_app = flask_app
        self.wsgi_app = wsgi_app
        self.cache_seconds = cache_seconds
        self._cached_at = 0.0
        self._cached_paths = (DEFAULT_ADMIN_PATH, DEFAULT_SUPER_ADMIN_PATH)

    def _paths(self):
        now = time.monotonic()
        if now - self._cached_at < self.cache_seconds:
            return self._cached_paths
        try:
            with self.flask_app.app_context():
                from app.utils import get_setting
                admin_path = normalize_panel_path(get_setting("admin_panel_path", ""), DEFAULT_ADMIN_PATH)
                super_path = normalize_panel_path(get_setting("super_admin_panel_path", ""), DEFAULT_SUPER_ADMIN_PATH)
                if admin_path == super_path:
                    super_path = DEFAULT_SUPER_ADMIN_PATH
                self._cached_paths = (admin_path, super_path)
                self._cached_at = now
        except Exception:
            pass
        return self._cached_paths

    @staticmethod
    def _matches(path, prefix):
        return path == prefix or path.startswith(prefix + "/")

    def __call__(self, environ, start_response):
        external_path = environ.get("PATH_INFO", "") or "/"
        admin_path, super_path = self._paths()
        environ["RTG_EXTERNAL_PATH"] = external_path
        environ["RTG_ADMIN_PUBLIC_PATH"] = admin_path
        environ["RTG_SUPER_ADMIN_PUBLIC_PATH"] = super_path

        if self._matches(external_path, super_path):
            environ["PATH_INFO"] = INTERNAL_SUPER_ADMIN_PATH + external_path[len(super_path):]
            environ["RTG_DYNAMIC_ADMIN_REWRITE"] = "1"
        elif self._matches(external_path, admin_path):
            environ["PATH_INFO"] = INTERNAL_ADMIN_PATH + external_path[len(admin_path):]
            environ["RTG_DYNAMIC_ADMIN_REWRITE"] = "1"
        elif (admin_path != INTERNAL_ADMIN_PATH and self._matches(external_path, INTERNAL_ADMIN_PATH)) or \
             (super_path != INTERNAL_SUPER_ADMIN_PATH and self._matches(external_path, INTERNAL_SUPER_ADMIN_PATH)):
            environ["RTG_BLOCK_INTERNAL_ADMIN_PATH"] = "1"

        return self.wsgi_app(environ, start_response)
