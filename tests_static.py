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

# Route aliases must be grouped before non-route decorators. Interleaving a
# limiter between two @blueprint.route decorators can make Flask register two
# different wrapper objects under the same endpoint and abort at startup.
for path in ROOT.glob('app/routes/*.py'):
    lines = path.read_text(encoding='utf-8').splitlines()
    decorators = []
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('@'):
            decorators.append((lineno, stripped))
            continue
        if stripped.startswith('def ') or stripped.startswith('async def '):
            route_positions = [i for i, (_, dec) in enumerate(decorators) if '.route(' in dec]
            if len(route_positions) > 1:
                first, last = min(route_positions), max(route_positions)
                between = decorators[first:last + 1]
                non_routes = [(ln, dec) for ln, dec in between if '.route(' not in dec]
                if non_routes:
                    errors.append(
                        f'{path}:{non_routes[0][0]} decorator non-route berada di antara alias route; '
                        'kelompokkan semua @...route berurutan untuk mencegah endpoint duplikat.'
                    )
            decorators = []
            continue
        if stripped and not stripped.startswith('#'):
            decorators = []

if errors:
    raise SystemExit('\n'.join(errors))
print('OK: sintaks Python, kebersihan cache, rute destruktif, dan urutan decorator lulus.')
