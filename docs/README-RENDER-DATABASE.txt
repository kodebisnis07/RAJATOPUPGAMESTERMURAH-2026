CATATAN PENTING RENDER / DATA TERSIMPAN

1. File ini sudah mendukung PostgreSQL Render lewat environment variable DATABASE_URL.
2. Kalau DATABASE_URL tidak diisi, aplikasi memakai SQLite rajatopup.db lokal.
3. Untuk website publik di Render, gunakan PostgreSQL agar data user/admin/order tidak hilang saat redeploy/restart.

Environment Variable minimal di Render:
- SECRET_KEY=isi_random_panjang
- FLASK_ENV=production
- DATABASE_URL=Internal Database URL dari PostgreSQL Render

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn run:app

Root Directory:
Isi sesuai folder repo Anda. Jika run.py ada di dalam folder raja-topup-games, isi: raja-topup-games
Jika run.py ada langsung di halaman utama repo, kosongkan Root Directory.

Akses login:
- User: /auth/login atau /login jika ada redirect di template
- Admin & Operator: /admin/login
- Super Admin: /super-admin/login atau /admin/login

Fitur hak akses:
- Super Admin full control.
- Admin/operator tidak bisa membuka menu Super Admin.
- Super Admin bisa mengatur izin Admin/Operator untuk reset password user dari menu Izin Role.
- Semua aktivitas penting admin/operator dicatat di Audit Log.
