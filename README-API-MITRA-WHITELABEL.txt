MODUL API MITRA / API RESELLER / WHITE LABEL
=============================================

Fitur yang ditambahkan:
- Menu Super Admin: API Management
- Menu Developer / Dokumentasi API
- Generate dan rotate API Key + API Secret
- Saldo khusus setiap mitra
- Markup harga API per mitra
- Pembatasan IP (opsional)
- Callback URL dan metadata White Label
- Log request API
- Endpoint produk, saldo, pembuatan order, dan status order
- Idempotency external_ref agar order yang sama tidak memotong saldo dua kali

Endpoint:
GET  /api/v1/ping
GET  /api/v1/balance
GET  /api/v1/products
POST /api/v1/order
GET  /api/v1/order/<external_ref>

Header autentikasi:
Authorization: Bearer <API_KEY>
X-API-Secret: <API_SECRET>

Cara menggunakan:
1. Login sebagai Super Admin.
2. Buka API Management.
3. Tambah Mitra API dan simpan API Key serta API Secret yang ditampilkan.
4. Isi saldo mitra dan markup harga.
5. Kirim kredensial kepada developer mitra melalui jalur aman.
6. Buka Developer / Dokumentasi API untuk contoh request.

PENTING:
- API Secret hanya ditampilkan ketika dibuat atau dirotasi.
- Jangan simpan API Secret di frontend/browser.
- Order API masuk dengan payment_status=paid dan order_status=processing.
- Integrasi pengiriman nyata ke Digiflazz masih harus disambungkan pada proses Auto Order/provider.
- Sebelum production, aktifkan HTTPS dan sebaiknya isi Allowed IP untuk setiap mitra.
