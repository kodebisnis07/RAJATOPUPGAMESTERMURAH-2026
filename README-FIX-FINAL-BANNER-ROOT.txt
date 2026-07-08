FIX FINAL BANNER + ROOT BERSIH

Isi ZIP ini sudah dibersihkan:
- Folder duplikat RAJATOPUPGAMES-TERMURAH2026 di dalam project dihapus.
- Folder .git lama dan cache __pycache__ dihapus.
- Banner utama otomatis memakai gambar baru rtg-banner-20260707.png.
- Data default banner lama di database akan otomatis diperbarui saat aplikasi start/deploy.
- Root Directory di Render harus DIKOSONGKAN.

Cara pakai:
1. Extract ZIP ini.
2. Masuk ke folder hasil extract.
3. Jalankan:
   git init
   git branch -M main
   git remote add origin https://github.com/kodebisnis07/RAJATOPUPGAMESTERMURAH-2026.git
   git add .
   git commit -m "fix final banner root bersih"
   git push -u origin main --force
4. Di Render: Settings -> Root Directory kosongkan.
5. Manual Deploy -> Deploy latest commit.
