import sqlite3
from concurrent.futures import ThreadPoolExecutor
from ctf.attempt_guard import reserve
from test_project import portal, verifier, artifacts, csrf, login, answer


def test_portal_rejects_guessing_after_cookie_clear(portal):
    client=portal.test_client()
    for _ in range(5):
        assert client.post('/review',data={'csrf':csrf(client),'transaction':'bad','audit':'bad'}).status_code==400
    fresh=portal.test_client()
    response=fresh.post('/review',data={'csrf':csrf(fresh),'transaction':'TX-217','audit':'AUD-217'})
    assert response.status_code==429
    assert int(response.headers['Retry-After'])>0
    assert fresh.get('/attachments/elias.enc.txt').status_code==403


def test_portal_guard_atomic_across_workers(tmp_path):
    path=tmp_path/'guard.sqlite'
    with ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(lambda _:reserve(path,'one-player'),range(10)))
    assert results.count(0)==5
    assert sum(v>0 for v in results)==5


def test_portal_hourly_allowance_and_independent_source(tmp_path):
    path=tmp_path/'guard.sqlite'
    assert reserve(path,'one',((60,100),(3600,2)))==0
    assert reserve(path,'one',((60,100),(3600,2)))==0
    assert reserve(path,'one',((60,100),(3600,2)))>0
    assert reserve(path,'two',((60,100),(3600,2)))==0


def test_verifier_hourly_limit_survives_relogin(verifier):
    import time
    client=login(verifier)
    with sqlite3.connect(verifier.config['DATABASE']) as db:
        db.executemany('INSERT INTO attempts VALUES (?,?)',[('alpha',time.time()-70)]*30)
    response=client.post('/verify',data=dict(csrf=csrf(client,'/verify'),**answer()))
    assert response.status_code==429
    with sqlite3.connect(verifier.config['DATABASE']) as db:
        assert db.execute('SELECT COUNT(*) FROM completions').fetchone()[0]==0
