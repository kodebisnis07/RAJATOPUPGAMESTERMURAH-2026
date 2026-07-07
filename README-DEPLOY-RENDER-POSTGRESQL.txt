LANGKAH CEPAT RENDER + POSTGRESQL

1. Render > New > PostgreSQL.
2. Copy Internal Database URL.
3. Render > Web Service > Environment.
4. Tambahkan:
   DATABASE_URL=Internal Database URL
   SECRET_KEY=random-panjang
   FLASK_ENV=production
   SESSION_COOKIE_SECURE=1
   SITE_URL=https://sky123fire.xyz
5. Build Command: pip install -r requirements.txt
6. Start Command: gunicorn run:app
7. Deploy.
8. Buka Render Shell lalu jalankan:
   flask init-db
   SUPERADMIN_USERNAME=superadmin SUPERADMIN_PASSWORD=passwordku flask create-superadmin

Jika registrasi user sebelumnya tidak tersimpan, penyebab paling umum adalah masih memakai SQLite di Render. Pastikan DATABASE_URL sudah terisi PostgreSQL.
