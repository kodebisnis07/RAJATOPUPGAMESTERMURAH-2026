import re
from flask import request
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

_FORM_RE = re.compile(r'(<form\b[^>]*\bmethod=["\']?post["\']?[^>]*>)', re.I)

def inject_csrf_into_html(response):
    """Tambahkan token CSRF ke semua form POST lama tanpa mengubah puluhan template."""
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type or response.direct_passthrough:
        return response
    try:
        html = response.get_data(as_text=True)
        if "<form" not in html.lower():
            return response
        token = generate_csrf()
        hidden = f'<input type="hidden" name="csrf_token" value="{token}">'
        html = _FORM_RE.sub(lambda m: m.group(1) + hidden, html)
        response.set_data(html)
        response.headers["Content-Length"] = str(len(response.get_data()))
    except Exception:
        pass
    return response


def init_security(app):
    csrf.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def _inject_csrf(response):
        return inject_csrf_into_html(response)
