"""Pemeriksaan tanpa dependency eksternal: jalankan `python tests_static.py`."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
errors = []
for path in [*ROOT.glob('*.py'), *ROOT.glob('app/**/*.py')]:
    try:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except Exception as exc:
        errors.append(f'{path}: {exc}')

junk = [p for p in ROOT.rglob('*') if p.name == '__pycache__' or p.suffix in {'.pyc', '.pyo'}]
if junk:
    errors.append(f'Cache Python masih ada: {len(junk)}')

admin = (ROOT / 'app/routes/admin.py').read_text(encoding='utf-8')
for marker in [
    '@admin_bp.route("/categories/delete/<int:id>", methods=["POST"])',
    '@admin_bp.route("/products/delete/<int:id>", methods=["POST"])',
]:
    if marker not in admin:
        errors.append(f'Rute destruktif belum POST-only: {marker}')

if errors:
    raise SystemExit('\n'.join(errors))
print('OK: sintaks Python, kebersihan cache, dan rute destruktif utama lulus.')
