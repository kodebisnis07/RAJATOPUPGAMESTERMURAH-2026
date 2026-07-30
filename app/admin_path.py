"""Dynamic public URLs for the admin panels.

Flask blueprints keep stable internal prefixes. This middleware maps configurable
public prefixes to those internal routes, then response rewriting keeps links,
forms, and redirects on the public URL used by the current request.

The built-in secret paths remain available as recovery aliases. This prevents an
administrator from being locked out when a database setting or Render environment
value is changed incorrectly.
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
    """Return a valid slash-prefixed panel path, otherwise ``fallback``."""
    slug = (value or "").strip().strip("/")
    if not slug:
        return fallback
    if not _SLUG_RE.fullmatch(slug) or slug.lower() in RESERVED_SLUGS:
        return fallback
    return "/" + slug


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
        self._env_admin_path = normalize_panel_path(
            flask_app.config.get("ADMIN_PANEL_PATH"), DEFAULT_ADMIN_PATH
        )
        self._env_super_path = normalize_panel_path(
            flask_app.config.get("SUPER_ADMIN_PANEL_PATH"), DEFAULT_SUPER_ADMIN_PATH
        )
        if self._env_admin_path.casefold() == self._env_super_path.casefold():
            self._env_super_path = DEFAULT_SUPER_ADMIN_PATH
        self._cached_paths = (self._env_admin_path, self._env_super_path)

    def invalidate(self):
        """Force the next request to reload panel paths from the database."""
        self._cached_at = 0.0

    def _paths(self):
        now = time.monotonic()
        if now - self._cached_at < self.cache_seconds:
            return self._cached_paths
        try:
            with self.flask_app.app_context():
                from app.utils import get_setting

                admin_path = normalize_panel_path(
                    get_setting("admin_panel_path", ""), self._env_admin_path
                )
                super_path = normalize_panel_path(
                    get_setting("super_admin_panel_path", ""), self._env_super_path
                )
                if admin_path.casefold() == super_path.casefold():
                    super_path = self._env_super_path
                    if admin_path.casefold() == super_path.casefold():
                        super_path = DEFAULT_SUPER_ADMIN_PATH
                self._cached_paths = (admin_path, super_path)
                self._cached_at = now
        except Exception:
            # Database may be unavailable during startup. Environment/default paths
            # still keep the panel reachable instead of returning a permanent 404.
            self._cached_paths = (self._env_admin_path, self._env_super_path)
            self._cached_at = now
        return self._cached_paths

    @staticmethod
    def _matches(path, prefix):
        """Match panel prefixes case-insensitively while preserving the suffix."""
        path_folded = path.casefold()
        prefix_folded = prefix.casefold()
        return path_folded == prefix_folded or path_folded.startswith(prefix_folded + "/")

    @staticmethod
    def _unique_paths(*paths):
        seen = set()
        result = []
        for path in paths:
            key = path.casefold()
            if key not in seen:
                seen.add(key)
                result.append(path)
        return result

    def __call__(self, environ, start_response):
        external_path = environ.get("PATH_INFO", "") or "/"
        admin_path, super_path = self._paths()

        # Accept the current database path, Render environment path, and the
        # built-in recovery path. The exact alias used is retained for generated
        # links and form actions, so the user is not redirected to an unknown URL.
        admin_aliases = self._unique_paths(
            admin_path, self._env_admin_path, INTERNAL_ADMIN_PATH
        )
        super_aliases = self._unique_paths(
            super_path, self._env_super_path, INTERNAL_SUPER_ADMIN_PATH
        )

        matched_admin = next(
            (prefix for prefix in admin_aliases if self._matches(external_path, prefix)),
            None,
        )
        matched_super = next(
            (prefix for prefix in super_aliases if self._matches(external_path, prefix)),
            None,
        )

        environ["RTG_EXTERNAL_PATH"] = external_path
        environ["RTG_ADMIN_PUBLIC_PATH"] = matched_admin or admin_path
        environ["RTG_SUPER_ADMIN_PUBLIC_PATH"] = matched_super or super_path

        # Super Admin is checked first in case a custom path happens to share a
        # textual prefix with the normal Admin path.
        if matched_super:
            environ["PATH_INFO"] = (
                INTERNAL_SUPER_ADMIN_PATH + external_path[len(matched_super):]
            )
            environ["RTG_DYNAMIC_ADMIN_REWRITE"] = "1"
        elif matched_admin:
            environ["PATH_INFO"] = INTERNAL_ADMIN_PATH + external_path[len(matched_admin):]
            environ["RTG_DYNAMIC_ADMIN_REWRITE"] = "1"

        return self.wsgi_app(environ, start_response)
