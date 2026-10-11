"""Generate new organizer secrets once; never overwrite an existing .env."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / '.env'
with path.open('x', encoding='utf-8') as f:
    for name in ('PORTAL_SECRET','VERIFIER_SECRET','CTFD_SECRET','DB_PASSWORD','DB_ROOT_PASSWORD'):
        f.write(name+'='+secrets.token_hex(32)+'\n')
try:
    path.chmod(0o600)
except OSError:
    pass
(root/'runtime/verifier-state').mkdir(parents=True,exist_ok=True)
print('Created private .env. On the Verifier VM: sudo chown 10001:10001 runtime/verifier-state')
