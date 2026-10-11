import json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
from urllib.request import urlopen
root=Path(__file__).resolve().parents[1]
os.chdir(root)
docker=shutil.which('docker') or next(p for p in (os.path.join(os.environ.get('ProgramFiles',''),'Docker/Docker/resources/bin/docker.exe'),os.path.join(os.environ.get('LOCALAPPDATA',''),'Programs/DockerDesktop/resources/bin/docker.exe')) if os.path.exists(p))
compose=[docker,'compose','--env-file','local/.env','-f','compose.local.yml']
checks=[]
def run(args,**kw):
    p=subprocess.run(args,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(f'Command failed: {args[:4]}\n{p.stderr.decode(errors="replace")[-1500:]}')
    return p.stdout
def check(name,condition):
    assert condition,name
    checks.append({'test':name,'status':'passed'})
    print('PASS: '+name,flush=True)
def state():
    out=run(compose+['exec','-T','ctfd','python','/bootstrap/state_snapshot.py']).decode()
    return json.loads(out.split('STATE_JSON:')[1].strip())
before=state()
backup=root/'local/private/backup-validation'
backup.mkdir(exist_ok=True)
dump=run([docker,'exec','last-backup-full-database-1','sh','-c','exec mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction ctfd'])
(backup/'ctfd.sql').write_bytes(dump)
check('Live CTFd SQL backup created',len(dump)>10000)
def sql(text):
    return run([docker,'exec','-i','last-backup-full-database-1','sh','-c','exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" --batch --skip-column-names'],input=text.encode()).decode()
restore='ctfd_restore_validation_20261010'
sql('CREATE DATABASE '+restore+';')
run([docker,'exec','-i','last-backup-full-database-1','sh','-c','exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" '+restore],input=dump)
tables=['users','challenges','flags','hints','submissions','unlocks','pages']
counts={}
for table in tables:
    original=sql(f'SELECT COUNT(*) FROM ctfd.{table};').strip()
    restored=sql(f'SELECT COUNT(*) FROM {restore}.{table};').strip()
    check('Restored SQL table matches: '+table,original==restored)
    counts[table]=int(restored)
# Compare row contents, including password hashes, flags, solve records and hint purchases.
for table in tables:
    check('Restored SQL rows match: '+table,sql(f'SELECT * FROM ctfd.{table} ORDER BY id;')==sql(f'SELECT * FROM {restore}.{table} ORDER BY id;'))
sql('DROP DATABASE '+restore+';')
sqlite_backup=run([docker,'exec','last-backup-full-verifier-1','python','-c',"import sqlite3,sys; from pathlib import Path; source=sqlite3.connect('/state/verifier.sqlite'); dest=sqlite3.connect('/tmp/verified-backup.sqlite'); source.backup(dest); dest.close(); sys.stdout.buffer.write(Path('/tmp/verified-backup.sqlite').read_bytes())"])
(backup/'verifier.sqlite').write_bytes(sqlite_backup)
with sqlite3.connect(backup/'verifier.sqlite') as db:
    check('Verifier backup integrity',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    check('Verifier backup retains completed test team',db.execute("SELECT COUNT(*) FROM completions WHERE team='validation-full'").fetchone()[0]==1)
    check('Verifier backup retains demo token record',db.execute("SELECT COUNT(*) FROM teams WHERE id='demo' AND enabled=1").fetchone()[0]==1)
uploads=run([docker,'exec','last-backup-full-ctfd-1','tar','-C','/var/uploads','-cf','-','.'])
(backup/'uploads.tar').write_bytes(uploads)
check('CTFd uploads archive saved',len(uploads)>0)
print('Restarting the full local stack...',flush=True)
run(compose+['restart','archive','portal','linux','verifier','ctfd','database','cache'])
for port,path in [(8001,'/'),(8081,'/'),(8083,'/health'),(8443,'/health')]:
    for attempt in range(30):
        try:
            if urlopen(f'http://127.0.0.1:{port}{path}',timeout=3).status==200:break
        except Exception:time.sleep(2)
    else:raise RuntimeError(f'Port {port} did not recover')
    check(f'Port {port} healthy after restart',True)
after=state()
check('CTFd accounts, solves, hint purchases and scores survive restart',before==after)
vstate=json.loads(run([docker,'exec','last-backup-full-verifier-1','python','-c',"import sqlite3,json; d=sqlite3.connect('/state/verifier.sqlite'); print(json.dumps({'completion':d.execute(\"SELECT COUNT(*) FROM completions WHERE team='validation-full'\").fetchone()[0],'attempts':d.execute(\"SELECT COUNT(*) FROM attempts WHERE team='validation-full'\").fetchone()[0]}))"]))
check('Verifier completion and attempt history survive restart',vstate['completion']==1 and vstate['attempts']==5)
ssh=['C:/Windows/System32/OpenSSH/ssh.exe','-i','local/private/analyst_key','-p','2222','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=local/private/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=10','analyst@127.0.0.1']
command='test ! -e /home/analyst/work/test-write && echo SCRATCH_RESET; test -r /srv/northstar/routes/EXIT-04.route && echo READABLE; test ! -w /srv/northstar/routes/EXIT-04.route && echo READONLY; touch /home/analyst/work/validation && echo SCRATCH_OK; test ! -e /usr/bin/sudo && echo NO_SUDO; cd /srv/northstar && sha256sum -c manifests/R17.sha256'
sshout=run(ssh+[command]).decode()
(root/'test-results/ssh-after-restart.log').write_text(sshout)
for token,label in [('SCRATCH_RESET','Linux scratch resets'),('READABLE','Linux evidence readable'),('READONLY','Linux evidence remains read-only'),('SCRATCH_OK','Linux scratch writable'),('NO_SUDO','Analyst has no sudo binary'),('OK','Trusted route checksum verified through real SSH')]:check(label,token in sshout)
inspect=json.loads(run([docker,'inspect']+['last-backup-full-'+s+'-1' for s in ['ctfd','database','cache','archive','portal','linux','verifier']]))
bindings=[]
for container in inspect:
    for port,values in (container['NetworkSettings']['Ports'] or {}).items():
        for value in values or []:bindings.append(value)
check('Exactly five player-facing ports',len(bindings)==5)
check('All published ports bound to loopback only',all(b['HostIp']=='127.0.0.1' for b in bindings))
check('Database and Redis not published',all(not c['HostConfig']['PortBindings'] for c in inspect if c['Name'] in ['/last-backup-full-database-1','/last-backup-full-cache-1']))
report={'status':'passed','checks':checks,'state_before':before,'state_after':after,'restored_table_counts':counts,'published_ports':bindings,'images':[{'container':c['Name'],'image_id':c['Image']} for c in inspect]}
(root/'test-results/operations.json').write_text(json.dumps(report,indent=2))
print('Operational checks passed: '+str(len(checks)),flush=True)
