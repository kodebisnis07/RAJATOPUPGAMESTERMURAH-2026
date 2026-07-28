# Deployment produksi

## Environment wajib

Isi `SECRET_KEY` acak minimal 32 karakter, `DATABASE_URL` PostgreSQL, URL Cloudinary, jalur panel rahasia, serta kredensial Super Admin. Gunakan Redis pada `RATELIMIT_STORAGE_URI` untuk deployment dengan lebih dari satu worker.

## Render

1. Hubungkan repository ke Render Blueprint memakai `render.yaml`.
2. Isi semua environment berlabel `sync: false`.
3. Deploy pertama menjalankan `flask init-db`, kemudian Gunicorn.
4. Setelah aktif, cek `/healthz` harus menghasilkan HTTP 200 dan `database: ok`.

## Lokal dengan Docker

Salin `.env.example` menjadi `.env`, gunakan nilai khusus lokal, lalu jalankan `docker compose up --build`.

## Checklist rilis

Jalankan `make test`, backup database, periksa callback payment di mode sandbox, lalu rotasi credential yang pernah tersebar. Jangan commit `.env`, database, export CSV, atau backup.
