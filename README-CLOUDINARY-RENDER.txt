CARA MENGAKTIFKAN CLOUDINARY DI RENDER
======================================

1. Buat akun Cloudinary dan buka Dashboard.
2. Salin nilai Cloud Name, API Key, dan API Secret.
3. Buka Render > layanan website Anda > Environment.
4. Tambahkan:

   MEDIA_STORAGE_BACKEND = cloudinary
   CLOUDINARY_URL = cloudinary://API_KEY:API_SECRET@CLOUD_NAME
   CLOUDINARY_FOLDER = rajatopupgames

5. Simpan lalu pilih Manual Deploy > Deploy latest commit.
6. Masuk panel admin dan upload satu gambar produk untuk pengujian.
7. Pastikan nilai gambar di database/halaman dimulai dengan:
   https://res.cloudinary.com/

CATATAN KEAMANAN
- Jangan memasukkan API Secret asli ke GitHub atau file .env.example.
- Simpan rahasia hanya di Environment Variables Render.
- File yang sudah ter-upload ke Cloudinary tidak hilang ketika Render restart, sleep, atau deploy ulang.
