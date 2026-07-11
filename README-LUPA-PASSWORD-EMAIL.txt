FITUR LUPA PASSWORD MELALUI EMAIL
=================================

Fitur yang ditambahkan:
1. Member memasukkan email terdaftar di /auth/lupa-password
2. Sistem mengirim link reset melalui SMTP
3. Link berlaku 1 jam (dapat diubah melalui PASSWORD_RESET_MAX_AGE)
4. Member membuat password baru dan kemudian login
5. Token lama otomatis tidak berlaku setelah password berhasil diganti
6. Respons halaman tidak membocorkan apakah suatu email terdaftar

PENGATURAN DI RENDER
--------------------
Tambahkan Environment Variables berikut:

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USE_SSL=0
MAIL_USERNAME=email-anda@gmail.com
MAIL_PASSWORD=app-password-google
MAIL_DEFAULT_SENDER=email-anda@gmail.com
PASSWORD_RESET_MAX_AGE=3600

Untuk Gmail, aktifkan Verifikasi 2 Langkah lalu buat Google App Password.
Jangan masukkan password Gmail biasa. Jangan commit nilai rahasia ke GitHub.

Setelah Environment Variables disimpan, lakukan Manual Deploy / Restart service.

ALUR PENGUJIAN
---------------
1. Pastikan akun member memiliki email yang benar.
2. Buka /auth/lupa-password
3. Masukkan email member.
4. Periksa Inbox dan Spam.
5. Klik tombol "Buat Password Baru".
6. Masukkan password baru minimal 6 karakter.
7. Login menggunakan password baru.

Jika email tidak masuk, periksa log Render untuk pesan "Gagal mengirim email reset password".
