"""Buat atau perbarui Super Admin dari environment variable."""
import os
from app import create_app
from app.extensions import db
from app.models import Admin

app = create_app()
with app.app_context():
    username = (os.environ.get("SUPERADMIN_USERNAME") or "").strip().lower()
    password = (os.environ.get("SUPERADMIN_PASSWORD") or "").strip()
    if not username or len(password) < 12:
        raise RuntimeError("Isi SUPERADMIN_USERNAME dan SUPERADMIN_PASSWORD minimal 12 karakter.")
    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        admin = Admin(username=username, name="Super Admin", role="super_admin", is_active=True)
        db.session.add(admin)
    admin.role = "super_admin"
    admin.is_active = True
    admin.set_password(password)
    db.session.commit()
    print(f"Super Admin siap: {username}")
