from app import create_app
from app.extensions import db
from app.models import Admin

app = create_app()

with app.app_context():
    admin = Admin.query.filter_by(username="admin").first()
    if not admin:
        admin = Admin(username="admin")
        db.session.add(admin)

    admin.name = "Super Admin"
    admin.role = "super_admin"
    admin.is_active = True
    admin.set_password("Admin@123")
    db.session.commit()

    print("Super Admin siap digunakan.")
    print("URL      : http://127.0.0.1:5000/admin/login")
    print("Username : admin")
    print("Password : Admin@123")
