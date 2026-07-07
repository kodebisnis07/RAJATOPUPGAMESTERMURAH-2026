FIX YANG DILAKUKAN:
1. Folder duplikat RAJATOPUPGAMES-TERMURAH2026 dihapus dari ZIP agar tidak membingungkan Git/Render.
2. Project sekarang langsung ada di root ZIP: app/, static/, templates/, run.py, requirements.txt, render.yaml.
3. Root Directory di Render harus DIKOSONGKAN.
4. Banner utama dipaksa memakai app/static/img/banner/rtg-banner-20260707.png.
5. Database lama yang berisi banner default tanpa gambar akan diperbaiki otomatis saat aplikasi start.
6. Menu admin dirapikan: Slide Banner Website dan Banner Website dipisahkan.

LANGKAH PAKAI:
- Extract ZIP ini.
- Copy semua isi folder hasil extract ke folder repo GitHub Anda.
- Jalankan:
  git add .
  git commit -m "fix banner root bersih"
  git push origin main
- Di Render: Settings > Root Directory dikosongkan.
- Manual Deploy > Deploy latest commit.
