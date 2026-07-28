PERUBAHAN MINIFY HTML / VIEW-SOURCE
===================================

Yang sudah diterapkan:
1. HTML hasil render otomatis diminifikasi.
2. Komentar HTML biasa otomatis dihapus.
3. Whitespace di antara tag dipadatkan.
4. Isi <pre>, <textarea>, <script>, dan <style> dipertahankan agar fungsi situs tidak rusak.
5. Fitur aktif secara default melalui environment:

   HTML_MINIFY_ENABLED=1

Untuk menonaktifkan sementara:

   HTML_MINIFY_ENABLED=0

PENTING:
Browser tetap harus menerima HTML, CSS, dan JavaScript agar website dapat tampil.
Karena itu view-source tidak bisa dinonaktifkan atau disembunyikan sepenuhnya.
Kode Python Flask, database, password, SECRET_KEY, dan API secret tetap berada di
server selama tidak pernah ditulis ke template/JavaScript publik.
