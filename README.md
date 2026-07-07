# Raja Topup Games v2.0 Production Ready

Versi ini sudah dirapikan untuk deploy di Render dengan PostgreSQL.

## Fitur yang ditambahkan/dirapikan

- PostgreSQL melalui `DATABASE_URL`.
- Kompatibel dengan URL Render `postgres://` dan `postgresql://`.
- Flask-Migrate/Alembic siap dipakai.
- `Procfile` dan `render.yaml` untuk Render.
- `.env.example` dan `.gitignore`.
- File `.git`, cache Python, database SQLite lokal, dan file duplikat dibersihkan dari paket deploy.
- `healthz` endpoint untuk monitoring.
- Error page 404 dan 500.
- Sitemap otomatis: `/sitemap.xml`.
- Robots.txt otomatis: `/robots.txt`.
- Export CSV via command `flask export-csv`.
- Command init database: `flask init-db`.
- Command buat super admin: `flask create-superadmin`.

## Deploy Render

1. Upload project ini ke GitHub.
2. Buat PostgreSQL di Render.
3. Buat Web Service dari repo GitHub.
4. Isi Environment:

```env
DATABASE_URL=Internal Database URL dari Render PostgreSQL
SECRET_KEY=random-panjang-yang-aman
FLASK_ENV=production
SESSION_COOKIE_SECURE=1
SITE_URL=https://sky123fire.xyz
SITE_NAME=Raja Topup Games
```

5. Build Command:

```bash
pip install -r requirements.txt
```

6. Start Command:

```bash
gunicorn run:app
```

## Command penting

Jalankan di Render Shell atau lokal:

```bash
flask init-db
flask create-superadmin
flask export-csv
```

Untuk membuat super admin custom:

```bash
SUPERADMIN_USERNAME=admin SUPERADMIN_PASSWORD=passwordku flask create-superadmin
```

## Migrasi database

Setelah dependencies terpasang:

```bash
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

Catatan: aplikasi tetap menjalankan `db.create_all()` agar deploy pertama tidak gagal, tetapi untuk produksi jangka panjang gunakan migration.

## URL penting

- Website: `/`
- Login user: `/login`
- Daftar: `/daftar`
- Admin: `/admin/login`
- Super Admin: `/super-admin/login`
- Sitemap: `/sitemap.xml`
- Robots: `/robots.txt`
- Health check: `/healthz`
