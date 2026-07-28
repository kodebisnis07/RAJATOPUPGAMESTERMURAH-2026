# Keamanan dan deployment

1. Isi `SECRET_KEY`, `DATABASE_URL`, jalur panel rahasia, dan kredensial Cloudinary melalui environment.
2. Jangan mengaktifkan `AUTO_CREATE_DB` atau `AUTO_SEED_DB` di production. Jalankan migrasi sebelum start aplikasi.
3. Buat Super Admin dengan `flask create-admin` atau isi `SUPERADMIN_USERNAME` dan `SUPERADMIN_PASSWORD` hanya saat seeding awal.
4. Callback Tripay berada di `/tripay/callback` dan menolak request tanpa `X-Callback-Signature` yang valid.
5. Untuk multi-instance, ganti `RATELIMIT_STORAGE_URI` dengan Redis agar limit login konsisten antar-worker.
6. Rotasi semua credential yang pernah tersimpan atau dibagikan dalam arsip lama.
