CARA MENJALANKAN RAJA TOPUP GAMES

1. Buka CMD di folder project yang berisi run.py.
2. Jalankan:
   pip install -r requirements.txt
   python create_admin.py
   python run.py

3. Buka website:
   http://127.0.0.1:5000

4. Login admin:
   http://127.0.0.1:5000/admin/login
   Username: admin
   Password: Admin@123

Catatan:
- Menu Nominal memakai data produk yang sama, tetapi tampil sebagai pengelolaan paket top-up.
- Payment gateway masih perlu credential asli/sandbox sebelum dipakai transaksi otomatis.
