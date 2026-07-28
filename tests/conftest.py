import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-12345")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUTO_CREATE_DB", "0")
os.environ.setdefault("AUTO_SEED_DB", "0")
os.environ.setdefault("SESSION_COOKIE_SECURE", "0")
os.environ.setdefault("WTF_CSRF_ENABLED", "0")

from app import create_app
from app.extensions import db

@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()
