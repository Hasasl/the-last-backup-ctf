"""Live reset test for the running local stack. Run from the project folder:
    python local/test_reset.py
Needs Docker Desktop running and the box started (Start Full Project.cmd).
It does NOT touch real scores: CTFd is only checked with -DryRun, the verifier
test uses a throw-away team called reset-test."""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
os.chdir(root)
docker = shutil.which('docker') or next((p for p in (
    os.path.join(os.environ.get('ProgramFiles', ''), 'Docker/Docker/resources/bin/docker.exe'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs/DockerDesktop/resources/bin/docker.exe')) if os.path.exists(p)), None)
if not docker:
    sys.exit('docker not found')
compose = [docker, 'compose', '--env-file', 'local/.env', '-f', 'compose.local.yml']
checks = []

def run(args, **kw):
    p = subprocess.run(args, capture_output=True, text=True, **kw)
    if p.returncode:
        raise RuntimeError(f'{args[:6]} failed:\n{p.stdout[-800:]}\n{p.stderr[-800:]}')
    return p.stdout

def check(name, ok):
    assert ok, name
    checks.append({'test': name, 'status': 'passed'})
    print('PASS: ' + name, flush=True)

def reset(*flags):
    return run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'local/reset.ps1', *flags])

def vsql(code, **env):
    args = compose + ['exec', '-T'] + sum((['-e', f'{k}={v}'] for k, v in env.items()), []) + ['verifier', 'python', '-']
    return run(args, input=code)

# 1. Linux scratch + evidence
run(compose + ['exec', '-T', 'linux', 'sh', '-c', 'echo leftover > /home/analyst/work/reset-test.txt'])
check('Scratch file created before reset', 'reset-test.txt' in run(compose + ['exec', '-T', 'linux', 'ls', '/home/analyst/work']))
out = reset('-Linux')
check('reset.ps1 -Linux reports OK', 'SCRATCH' not in out and 'FAILED' not in out)
check('Scratch file gone after reset', 'reset-test.txt' not in run(compose + ['exec', '-T', 'linux', 'ls', '/home/analyst/work']))
check('Evidence rebuilt and readable', run(compose + ['exec', '-T', 'linux', 'test', '-s', '/srv/northstar/routes/EXIT-04.route']) == '')

# 2. Verifier: one throw-away team, other teams untouched
seed = ("import sqlite3,time\nd=sqlite3.connect('/state/verifier.sqlite')\n"
        "d.execute(\"INSERT OR REPLACE INTO teams(id,token_hash) VALUES ('reset-test','x')\")\n"
        "d.execute(\"INSERT OR IGNORE INTO completions VALUES ('reset-test',?)\",(time.time(),))\n"
        "[d.execute(\"INSERT INTO attempts VALUES ('reset-test',?)\",(time.time(),)) for _ in range(3)]\nd.commit()\n")
count = ("import sqlite3\nd=sqlite3.connect('/state/verifier.sqlite')\n"
         "one=lambda sql:d.execute(sql).fetchone()[0]\n"
         "print('C',one(\"SELECT COUNT(*) FROM completions WHERE team='reset-test'\"),"
         "one(\"SELECT COUNT(*) FROM attempts WHERE team='reset-test'\"),"
         "one(\"SELECT COUNT(*) FROM completions WHERE team!='reset-test'\"),"
         "one('SELECT COUNT(*) FROM teams'))\n")
vsql(seed)
before = vsql(count).split()
check('Throw-away team has progress', before[1] == '1' and before[2] == '3')
reset('-Verifier', '-Team', 'reset-test')
after = vsql(count).split()
check('Team progress cleared', after[1] == '0' and after[2] == '0')
check('Other teams untouched', after[3] == before[3])
check('Team tokens kept', after[4] == before[4])
vsql("import sqlite3\nd=sqlite3.connect('/state/verifier.sqlite')\nd.execute(\"DELETE FROM teams WHERE id='reset-test'\")\nd.commit()\n")

# 3. Portal secret rotation
env_path = root / 'local/.env'
secret = lambda: re.search(r'(?m)^PORTAL_SECRET=(\S+)', env_path.read_text()).group(1)
old = secret()
reset('-Portal')
check('PORTAL_SECRET rotated', secret() != old)
check('Portal healthy after reset', json.load(urlopen('http://127.0.0.1:8083/health', timeout=10))['status'] == 'ok')

# 4. CTFd dry run changes nothing
snap = lambda: run(compose + ['exec', '-T', 'ctfd', 'python', '/bootstrap/state_snapshot.py']).split('STATE_JSON:')[1].strip()
s1 = snap()
out = reset('-Scores', '-DryRun')
check('CTFd dry run reports nothing changed', 'Dry run: nothing was changed' in out)
check('CTFd state identical after dry run', snap() == s1)

(root / 'test-results').mkdir(exist_ok=True)
(root / 'test-results/reset-tests.json').write_text(json.dumps({'run_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'checks': checks}, indent=2))
print(f'{len(checks)} reset checks passed')
