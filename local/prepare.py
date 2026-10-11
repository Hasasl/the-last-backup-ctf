"""Prepare a separate localhost deployment without changing the original lab."""
import json, secrets
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
private = root/'local/private'
private.mkdir(parents=True, exist_ok=True)
env = root/'local/.env'
if not env.exists():
    values = {k: secrets.token_hex(24) for k in ('CTFD_SECRET','DB_PASSWORD','DB_ROOT_PASSWORD','PORTAL_SECRET','VERIFIER_SECRET','ADMIN_PASSWORD')}
    values.update(ADMIN_NAME='organizer', ADMIN_EMAIL='organizer@example.test')
    env.write_text(''.join(f'{k}={v}\n' for k,v in values.items()))
    (private/'organizer-login.txt').write_text('Full project: http://localhost:8001\nUsername: organizer\nPassword: '+values['ADMIN_PASSWORD']+'\n')

compose = {'name':'last-backup-full', 'services':{}, 'volumes':{}, 'networks':{}}
for name in ('control','challenge','linux','verifier'):
    part = yaml.safe_load((root/f'compose.{name}.yml').read_text())
    for key in ('services','volumes','networks'):
        compose[key].update(part.get(key,{}))
s = compose['services']
del s['control-web'], s['portal-web'], s['verifier-web']
s['ctfd']['ports'] = ['127.0.0.1:8001:8000']
s['ctfd']['environment'].update(ADMIN_NAME='${ADMIN_NAME}',ADMIN_EMAIL='${ADMIN_EMAIL}',ADMIN_PASSWORD='${ADMIN_PASSWORD}',REVERSE_PROXY='0')
s['ctfd']['volumes'] += ['./local/private:/bootstrap:ro','./build/organizer:/organizer:ro']
s['ctfd']['networks'] = ['web','data']
s['ctfd']['volumes'].append('./local/theme:/opt/CTFd/CTFd/themes/northstar:ro')
s['ctfd']['volumes'].append('./local/plugins/northstar_replay:/opt/CTFd/CTFd/plugins/northstar_replay:ro')
s['archive']['ports'] = ['127.0.0.1:8081:8081']
s['portal']['ports'] = ['127.0.0.1:8083:8000']
s['verifier']['ports'] = ['127.0.0.1:8443:8000']
# HTTP is confined to loopback. The original four-VM HTTPS configuration is preserved.
s['verifier']['command'] = ['gunicorn','--bind','0.0.0.0:8000','--workers','2','--threads','2','--access-logfile','-','local_wsgi:app']
s['verifier']['volumes'] = ['./build/verifier:/data:ro','verifier-state:/state','./local/local_wsgi.py:/app/local_wsgi.py:ro']
compose['volumes']['verifier-state'] = None
s['linux']['ports'] = ['127.0.0.1:2222:22']
s['linux']['volumes'][1] = './local/private/analyst_authorized_keys:/etc/ssh/authorized_keys/analyst:ro'
entrypoint=(root/'deploy/linux/entrypoint.sh').read_text().replace('exec /usr/sbin/sshd -D -e','install -m 644 /etc/ssh/authorized_keys/analyst /run/analyst_authorized_keys\nexec /usr/sbin/sshd -D -e -o AuthorizedKeysFile=/run/analyst_authorized_keys')
(root/'local/linux-entrypoint.sh').write_text(entrypoint,newline='\n')
s['linux']['volumes'].append('./local/linux-entrypoint.sh:/local-entrypoint.sh:ro')
s['linux']['entrypoint']=['/bin/sh','/local-entrypoint.sh']
# Docker Desktop does not publish these ports on internal-only networks.
# Separate loopback-facing bridges keep each challenge separate; DB stays internal.
for service in s.values():
    if 'networks' not in service: continue
    service['networks'] = [n if n == 'data' else 'local-'+n for n in service['networks']]
compose['networks'] = {'data': {'internal': True}, **{'local-'+n:{} for n in ('web','archive','portal','evidence','verifier')}}
s['verifier-init'] = {'build':'.','image':'last-backup-full-verifier','user':'0:0','command':['chown','10001:10001','/state'],'volumes':['verifier-state:/state'],'network_mode':'none','restart':'no'}
s['verifier']['depends_on'] = {'verifier-init':{'condition':'service_completed_successfully'}}
if 'portal-state:/state' not in s['portal']['volumes']: s['portal']['volumes'].append('portal-state:/state')
compose['volumes']['portal-state'] = None
s['portal-init'] = {'image':'last-backup-full-portal','build':'.','user':'0:0','command':['chown','10001:10001','/state'],'volumes':['portal-state:/state'],'network_mode':'none','restart':'no'}
s['portal']['depends_on'] = {'portal-init':{'condition':'service_completed_successfully'}}
(root/'compose.local.yml').write_text(yaml.safe_dump(compose,sort_keys=False))
(root/'local/local_wsgi.py').write_text("from ctf.wsgi import app\napp.config['SESSION_COOKIE_SECURE'] = False\n")
print('Local configuration prepared; private credentials saved.')
