FIX ADMIN PANEL RAHASIA

Yang ditambahkan:
1. Link /admin lama diblokir 404.
2. Link /super-admin lama diblokir 404.
3. Panel admin/operator sekarang memakai link rahasia:
   /panel-rtg-2026-X7q9K/login
4. Panel super admin sekarang memakai link rahasia:
   /super-panel-rtg-2026-S9kL2/login
5. Semua halaman panel tetap wajib login admin aktif.
6. Role tetap dibatasi oleh kode role_required yang sudah ada:
   - super_admin: full akses
   - admin: akses admin
   - operator: akses operasional sesuai izin route

URL lengkap contoh Render:
https://rajatopupgames-termurah2026.onrender.com/panel-rtg-2026-X7q9K/login

Jika ingin mengganti link rahasia di Render:
1. Buka Render > Service website > Environment.
2. Tambahkan:
   ADMIN_PANEL_PATH=/link-rahasia-anda
   SUPER_ADMIN_PANEL_PATH=/link-super-rahasia-anda
3. Manual Deploy > Clear build cache & deploy.

PENTING:
Jangan bagikan link rahasia ini ke user biasa.
