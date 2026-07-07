import csv
import os
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models import User, Order, Payment, Admin


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def register_cli(app):
    """Command operasional: init-db, export CSV, dan backup ringan."""

    @app.cli.command("init-db")
    def init_db():
        """Buat semua tabel dan seed data awal."""
        db.create_all()
        from app.seed import seed_initial_data
        seed_initial_data()
        print("Database siap digunakan.")

    @app.cli.command("create-superadmin")
    def create_superadmin():
        """Buat super admin default jika belum ada."""
        username = os.environ.get("SUPERADMIN_USERNAME", "superadmin").strip().lower()
        password = os.environ.get("SUPERADMIN_PASSWORD", "admin12345").strip()
        admin = Admin.query.filter_by(username=username).first()
        if not admin:
            admin = Admin(username=username, name="Super Admin", role="super_admin", is_active=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
        print(f"Super admin siap: {username}")

    @app.cli.command("export-csv")
    def export_csv():
        """Export data user, order, dan payment ke folder exports/."""
        out_dir = _ensure_dir(os.path.join(current_app.root_path, "..", "exports"))
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

        files = []
        user_path = os.path.join(out_dir, f"users-{stamp}.csv")
        with open(user_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "name", "username", "email", "phone", "member_level", "balance", "is_active", "created_at"])
            for u in User.query.order_by(User.id.asc()).all():
                w.writerow([u.id, u.name, u.username, u.email, u.phone, u.member_level, u.balance, u.is_active, u.created_at])
        files.append(user_path)

        order_path = os.path.join(out_dir, f"orders-{stamp}.csv")
        with open(order_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "invoice", "user_id", "product_id", "price", "payment_status", "order_status", "created_at"])
            for o in Order.query.order_by(Order.id.asc()).all():
                w.writerow([o.id, o.invoice, o.user_id, o.product_id, o.price, o.payment_status, o.order_status, o.created_at])
        files.append(order_path)

        payment_path = os.path.join(out_dir, f"payments-{stamp}.csv")
        with open(payment_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "order_id", "payment_name", "provider", "amount", "status", "created_at"])
            for p in Payment.query.order_by(Payment.id.asc()).all():
                w.writerow([p.id, p.order_id, p.payment_name, p.provider, p.amount, p.status, p.created_at])
        files.append(payment_path)

        print("Export selesai:")
        for file_path in files:
            print(file_path)
