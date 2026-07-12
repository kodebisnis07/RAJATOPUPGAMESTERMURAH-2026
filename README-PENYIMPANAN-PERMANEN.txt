PERBAIKAN PENYIMPANAN PERMANEN - RAJA TOPUP GAMES
===================================================

Arsitektur production:
1. PostgreSQL Render menyimpan data produk, user, order, pengaturan, dan URL gambar.
2. Cloudinary menyimpan file gambar secara permanen.
3. Database tidak menyimpan isi file gambar; database menyimpan URL HTTPS Cloudinary.

Environment Render yang wajib:
DATABASE_URL=<Internal Database URL PostgreSQL dari Render>
MEDIA_STORAGE_BACKEND=cloudinary
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
CLOUDINARY_FOLDER=rajatopupgames

Setelah mengubah Environment:
1. Save Changes.
2. Manual Deploy -> Deploy latest commit.
3. Upload satu gambar produk baru.
4. Pastikan gambar muncul di Cloudinary Media Library pada folder rajatopupgames/products.
5. Restart service Render dan cek lagi gambar tersebut.

Catatan:
- Gambar lokal lama tetap kompatibel dan masih dapat ditampilkan.
- Upload baru masuk ke Cloudinary.
- URL gambar baru disimpan ke PostgreSQL.
- Kolom media PostgreSQL otomatis diperlebar menjadi VARCHAR(500) saat aplikasi mulai.
- Jangan menyimpan CLOUDINARY_URL/API_SECRET ke GitHub.
