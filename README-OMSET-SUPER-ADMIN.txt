Fitur Riwayat Omset Super Admin

Menu baru:
- Panel Admin / Super Admin -> 📈 Riwayat Omset
- URL langsung: /admin/omset atau /super-admin/omset

Yang ditampilkan:
- Omset Hari Ini
- Omset Bulan Ini
- Omset Bulan Lalu
- Total Omset Paid
- Riwayat omset bulanan 24 bulan
- Riwayat omset harian 31 hari

Catatan penting:
Omset dihitung otomatis dari tabel orders dengan payment_status = paid.
Omset Bulan Ini otomatis reset ketika tanggal masuk bulan baru karena query memakai rentang tanggal bulan berjalan. Data bulan lama tidak hilang, tetap muncul di Riwayat Omset Bulanan.
