from flask_sqlalchemy import SQLAlchemy

try:
    from flask_migrate import Migrate
except Exception:  # fallback agar aplikasi lokal tetap jalan jika dependensi belum di-install
    class Migrate:  # type: ignore
        def init_app(self, *args, **kwargs):
            return None

# Ekstensi aplikasi diletakkan di satu file agar mudah dirawat.
db = SQLAlchemy()
migrate = Migrate()
