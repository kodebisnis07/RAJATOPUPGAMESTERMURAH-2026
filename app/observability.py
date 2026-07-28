import logging
import os
import time
import uuid
from flask import g, request, has_request_context


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(g, "request_id", "-") if has_request_context() else "-"
        return True


def init_observability(app):
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s: %(message)s"
    ))
    handler.addFilter(RequestContextFilter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)

    @app.before_request
    def _request_start():
        supplied = (request.headers.get("X-Request-ID") or "").strip()
        g.request_id = supplied[:100] if supplied else uuid.uuid4().hex
        g.request_started_at = time.monotonic()

    @app.after_request
    def _request_finish(response):
        elapsed_ms = int((time.monotonic() - getattr(g, "request_started_at", time.monotonic())) * 1000)
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        app.logger.info(
            "%s %s status=%s duration_ms=%s ip=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            request.remote_addr,
        )
        return response
