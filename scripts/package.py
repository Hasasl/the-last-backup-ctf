"""Create an organizer ZIP. Runtime secrets and local environments are excluded."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
target = root.parent / 'The-Last-Backup-Implementation.zip'
excluded = {'runtime','.venv','__pycache__','.pytest_cache','.git'}
with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as archive:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if not path.is_file() or excluded.intersection(relative.parts) or path.name=='.env':
            continue
        archive.write(path, 'last-backup/'+relative.as_posix())
print(f'Organizer source/evidence package: {target} ({target.stat().st_size:,} bytes)')
