import hashlib
import importlib.util
import json
import re
import sqlite3
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
import yaml
from build import build, FLAGS
from ctf.cipher import transform
from ctf.portal import create_app as portal_app
from ctf.verifier import create_app as verifier_app
from manage import issue_team
from scripts.solve import extract_png, recover_fat, timeline
from scripts.seed_ctfd import seed

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='session')
def artifacts(tmp_path_factory):
    out = tmp_path_factory.mktemp('release')
    build(out)
    return out

def csrf(client, path='/'):
    response = client.get(path)
    match = re.search(rb'name="csrf" value="([^"]+)"', response.data)
    assert match, response.data
    return match[1].decode()

@pytest.fixture
def portal(artifacts, tmp_path):
    return portal_app(dict(TESTING=True, SECRET_KEY='test-only', DATA_DIR=artifacts/'portal', GUARD_DATABASE=tmp_path/'portal-guard.sqlite'))

@pytest.fixture
def verifier(artifacts, tmp_path):
    config = dict(TESTING=True, SECRET_KEY='test-only', ANSWER_FILE=artifacts/'verifier/answer.json', DATABASE=tmp_path/'state.sqlite')
    return verifier_app(config)

def login(app, team='alpha'):
    token = issue_team(app.config['DATABASE'], team)
    client = app.test_client()
    assert client.post('/', data=dict(csrf=csrf(client),token=token)).status_code == 302
    return client

def answer():
    return dict(release_id='R17',route_id='EXIT-04',service='mn-sync',event_id='EVT-024')

def test_cipher_convention():
    assert transform('ABC abc!') == 'OSC cmg!'
    sample = 'FLAG{st04_é_123}\nSecond LINE!'
    assert transform(transform(sample),decrypt=True) == sample
    assert transform('A\nB') == transform('AB')[0]+'\n'+transform('AB')[1]
    with pytest.raises(ValueError): transform('abc','')

def test_osint_unique(artifacts):
    pages = list((artifacts/'stage1').glob('notice-*.html'))
    matches = [p for p in pages if 'MN06-0217' in p.read_text(encoding='utf-8') and '2026-02-17 01:40 UTC' in p.read_text(encoding='utf-8')]
    assert len(matches) == 1
    assert FLAGS[0] in matches[0].read_text(encoding='utf-8')

def test_image_note(artifacts):
    text = extract_png(artifacts/'stage1/event-original.png')
    assert FLAGS[1] in text and 'APR-0217' in text
    assert 'http://127.0.0.1:8083' in text

def test_integrity_chain(artifacts):
    plaintext = transform((artifacts/'portal/elias.enc.txt').read_text(), decrypt=True)
    assert FLAGS[3] in plaintext
    assert hashlib.sha256((artifacts/'handouts/northstar_evidence.img').read_bytes()).hexdigest() in plaintext
    files = recover_fat(artifacts/'handouts/northstar_evidence.img')
    assert FLAGS[4] in files['_ANDOVER.TXT']
    assert FLAGS[5] not in ''.join(files.values())
    evidence = timeline(files)
    assert evidence['service'] == 'mn-sync'
    assert evidence['start'].endswith('02:17:00Z') and evidence['end'].endswith('02:34:00Z')
    manifest = artifacts/'linux/manifests/R17.sha256'
    assert evidence['manifest_sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    line = next(line for line in manifest.read_text().splitlines() if not line.startswith('#'))
    checksum, path = line.split()
    assert checksum == hashlib.sha256((artifacts/'linux'/path).read_bytes()).hexdigest()

def test_fat_independent_library(artifacts):
    from pyfatfs.PyFatFS import PyFatFS
    with PyFatFS(str(artifacts/'handouts/northstar_evidence.img'), read_only=True) as fs:
        assert 'SESSION.LOG' in fs.listdir('/')
        assert 'HANDOVER.TXT' not in fs.listdir('/')
        assert 'S-217' in fs.readtext('/SESSION.LOG')

def test_tar_link_permissions_no_flag(artifacts):
    with tarfile.open(artifacts/'organizer/linux-evidence.tar') as archive:
        link = archive.getmember('CURRENT_EXIT')
        assert link.issym() and link.linkname=='routes/EXIT-09.route'
        for member in archive.getmembers():
            if member.isfile():
                assert member.mode == 0o440
                assert not any(flag.encode() in archive.extractfile(member).read() for flag in FLAGS)

def test_build_reproducible(artifacts,tmp_path):
    other = tmp_path/'again'
    build(other)
    for relative in ['handouts/northstar_evidence.img','portal/elias.enc.txt','stage1/event-original.png','organizer/linux-evidence.tar']:
        assert (artifacts/relative).read_bytes() == (other/relative).read_bytes()

def test_portal_gates_all_attachments(portal):
    client = portal.test_client()
    assert client.get('/attachments/elias.enc.txt').status_code == 403
    assert FLAGS[2].encode() not in client.get('/').data
    assert client.post('/review',data={'transaction':'TX-217','audit':'AUD-217'}).status_code == 400
    response = client.post('/review',data=dict(csrf=csrf(client),transaction='TX-211',audit='AUD-217'))
    assert response.status_code==400 and FLAGS[2].encode() not in response.data
    assert client.get('/attachments/training-memo.txt').status_code == 403
    assert client.get('/private.json').status_code == 404

def test_portal_right_pair_and_session_isolation(portal):
    client = portal.test_client()
    response = client.post('/review',data=dict(csrf=csrf(client),transaction='TX-217',audit='AUD-217'))
    assert response.status_code==200 and FLAGS[2].encode() in response.data
    assert client.get('/attachments/elias.enc.txt').status_code == 200
    assert client.get('/attachments/../private.json').status_code == 404
    assert portal.test_client().get('/attachments/elias.enc.txt').status_code == 403

def test_portal_denied_event_not_proof(portal):
    client = portal.test_client()
    assert client.post('/review',data=dict(csrf=csrf(client),transaction='TX-217',audit='AUD-219')).status_code == 400

def test_audit_filter_and_headers(portal):
    client = portal.test_client()
    response = client.get('/api/audit?reference=APR-0217')
    assert len(response.json)==3
    assert all(x['reference']=='APR-0217' for x in response.json)
    assert response.headers['X-Content-Type-Options']=='nosniff'
    assert 'no-store' in response.headers['Cache-Control']

def test_verifier_anonymous_and_bad_token(verifier):
    client = verifier.test_client()
    assert client.get('/verify').status_code == 302
    assert client.post('/',data=dict(csrf=csrf(client),token='wrong')).status_code == 403
    assert client.get('/answer.json').status_code == 404

def test_verifier_generic_failure(verifier):
    client = login(verifier)
    token = csrf(client,'/verify')
    messages=[]
    for field in answer():
        values=answer(); values[field]='wrong'
        response=client.post('/verify',data={**values,'csrf':token})
        assert response.status_code==400 and FLAGS[5].encode() not in response.data
        assert b'Evidence does not match the trusted recovery record.' in response.data

def test_verifier_correct_trim_and_persistence(verifier):
    client=login(verifier)
    response=client.post('/verify',data={**{k:' '+v+' ' for k,v in answer().items()},'csrf':csrf(client,'/verify')})
    assert response.status_code==200 and FLAGS[5].encode() in response.data
    again=verifier_app(verifier.config)
    with sqlite3.connect(again.config['DATABASE']) as db:
        assert db.execute('SELECT count(*) FROM completions').fetchone()[0]==1

def test_rate_limit_persists_and_is_per_team(verifier):
    client=login(verifier)
    token=csrf(client,'/verify')
    for i in range(5):
        assert client.post('/verify',data={'csrf':token}).status_code==400
    assert client.post('/verify',data={**answer(),'csrf':token}).status_code==429
    restarted=verifier_app(verifier.config)
    other=login(restarted,'beta')
    assert other.post('/verify',data={**answer(),'csrf':csrf(other,'/verify')}).status_code==200
    with sqlite3.connect(verifier.config['DATABASE']) as db:
        db.execute('UPDATE attempts SET at=at-61 WHERE team=?',('alpha',))
    assert client.post('/verify',data={**answer(),'csrf':token}).status_code==200

def test_concurrent_attempt_limit(verifier):
    token=issue_team(verifier.config['DATABASE'],'parallel')
    clients=[]
    for i in range(8):
        client=verifier.test_client()
        client.post('/',data={'csrf':csrf(client),'token':token})
        clients.append((client,csrf(client,'/verify')))
    def post(pair):
        return pair[0].post('/verify',data={'csrf':pair[1]}).status_code
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes=list(pool.map(post,clients))
    assert codes.count(400)==5 and codes.count(429)==3

def test_revoked_team_session_denied(verifier):
    client=login(verifier)
    with sqlite3.connect(verifier.config['DATABASE']) as db:
        db.execute('UPDATE teams SET enabled=0 WHERE id="alpha"')
    assert client.get('/verify').status_code==302

def test_login_rate_limit(verifier):
    client=verifier.test_client(); token=csrf(client)
    for i in range(10):
        assert client.post('/',data={'csrf':token,'token':'bad'}).status_code==403
    assert client.post('/',data={'csrf':token,'token':'bad'}).status_code==429

@pytest.mark.parametrize('filename,count',[('challenges.json',6),('challenges-split5.json',7)])
def test_ctfd_seed_order_and_score(artifacts,filename,count):
    challenges=json.loads((artifacts/'organizer'/filename).read_text())
    calls=[]
    def fake(base,token,method,path,data=None):
        calls.append((method,path,data))
        if method=='GET': return []
        return {'id':len([c for c in calls if c[:2]==('POST','/challenges')])}
    ids=seed('http://local','token',challenges,dict(archive_url='A',portal_url='P',verifier_url='V'),fake)
    assert len(ids)==count
    assert sum(c['value'] for c in challenges)==1150
    assert len([c for c in calls if c[:2]==('POST','/flags')])==count
    assert all(c[2]['state']=='hidden' for c in calls if c[:2]==('POST','/challenges'))
    prereqs=[c for c in calls if c[0]=='PATCH' and 'requirements' in c[2]]
    assert len(prereqs)==count-1

def test_deployment_no_database_ports():
    control=yaml.safe_load((ROOT/'compose.control.yml').read_text())
    assert 'ports' not in control['services']['database']
    assert 'ports' not in control['services']['cache']
    assert 'ports' not in control['services']['ctfd']
    for filename in ROOT.glob('compose.*.yml'):
        config=yaml.safe_load(filename.read_text())
        if filename.name in ('compose.local.yml', 'compose.replay-test.yml'):
            assert config['networks']['data']['internal'] is True
            assert 'ports' not in config['services']['database']
            assert 'ports' not in config['services']['cache']
            published=[p for s in config['services'].values() for p in s.get('ports',[])]
            assert len(published)==(5 if filename.name == 'compose.local.yml' else 1)
            assert all(p.startswith('127.0.0.1:') for p in published)
            if filename.name == 'compose.replay-test.yml':
                assert config['name'] == 'last-backup-v4-test'
                assert all(v['name'].startswith('last-backup-v4-test_') for v in config['volumes'].values())
        else:
            assert all(n['internal'] for n in config['networks'].values())
