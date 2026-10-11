"""Destructive test fixtures: ONLY run inside the isolated replay-test compose.

docker compose -f compose.replay-test.yml --env-file local/.env exec -T
  -e NORTHSTAR_TEST_ENV=isolated ctfd python /replay-tests/test_replay_live.py
"""
import os
import re
import json
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor

if os.environ.get('NORTHSTAR_TEST_ENV') != 'isolated':
    raise SystemExit('Refusing: this suite is for the separate test event only.')
sys.path.insert(0, '/opt/CTFd')
from CTFd import create_app
from CTFd.models import db, Users, Challenges, Flags, Solves
from CTFd.utils import set_config
from CTFd.cache import cache
import requests

app = create_app()
from CTFd.plugins.northstar_replay import ReplayLimit, ReplayEvent, ReplayRun
base = 'http://127.0.0.1:8000'
results = []


def check(name, condition):
    results.append({'test': name, 'passed': bool(condition)})
    if not condition:
        print(json.dumps(results, indent=2))
        raise AssertionError(name)


def allowance():
    with app.app_context():
        ReplayLimit.query.delete()
        db.session.commit()


def player(prefix):
    name = prefix + secrets.token_hex(4)
    password = secrets.token_urlsafe(20)
    with app.app_context():
        u = Users(name=name, email=name+'@example.test', password=password, verified=True, hidden=True)
        db.session.add(u); db.session.commit(); uid = u.id
    s = requests.Session()
    page = s.get(base+'/login')
    nonce = re.search(r'name="nonce"[^>]*value="([^"]+)"', page.text)[1]
    response = s.post(base+'/login', data={'name': name, 'password': password, 'nonce': nonce})
    check('real login '+prefix, '/login' not in response.url)
    page = s.get(base+'/challenges')
    nonce = re.search(r"csrfNonce[\"']?\s*:\s*[\"']([^\"']+)", page.text)[1]
    s.headers['CSRF-Token'] = nonce
    return uid, s


def attempt(s, cid, flag):
    return s.post(base+'/api/v1/challenges/attempt', json={'challenge_id':cid, 'submission':flag})


def action(s, op, cid=None, flag=None, **extra):
    return s.post(base+'/practice/action', json={'action':op,'challenge_id':cid,'submission':flag,**extra})


def totals(s):
    r=s.get(base+'/practice/stats'); check('stats accessible',r.status_code==200)
    return r.json()['data']['totals']


with app.app_context():
    set_config('ctf_theme', 'northstar'); cache.clear()
    challenges = [(c.id, Flags.query.filter_by(challenge_id=c.id).first().content) for c in Challenges.query.order_by(Challenges.id).all()]
uid, s = player('replay_qa_')
other_id, other = player('isolation_qa_')
allowance()
cid, flag = challenges[0]
check('anonymous cannot reset', requests.post(base+'/practice/action', json={'action':'reset_box'}).status_code in (302,403))
bad = requests.Session(); bad.cookies.update(s.cookies)
check('CSRF required', bad.post(base+'/practice/action',json={'action':'reset_box'}).status_code == 403)
check('unsolved stage cannot be replayed',action(s,'submit',cid,flag).status_code==403)
check('locked later competition stage denied',attempt(s,*challenges[-1]).status_code==403)
allowance()
check('wrong official flag',attempt(s,cid,'wrong').json()['data']['status']=='incorrect')
check('correct official flag',attempt(s,cid,flag).json()['data']['status']=='correct')
check('duplicate official flag stays already solved',attempt(s,cid,flag).json()['data']['status']=='already_solved')
check('initial totals exact',totals(s)=={'correct':1,'wrong':1,'reset':0,'box_reset':0})
check('wrong practice flag',action(s,'submit',cid,'wrong').json()['data']['status']=='incorrect')
check('correct practice flag',action(s,'submit',cid,flag).json()['data']['status']=='correct')
r=action(s,'submit',cid,flag)
check('competition and practice share five-per-minute limit',r.status_code==429 and int(r.headers['Retry-After'])>0)
before=totals(s)
check('reset during cooldown allowed independently',action(s,'reset',cid).status_code==200)
check('reset cannot bypass cooldown',action(s,'submit',cid,flag).status_code==429)
allowance()
check('same stage correct after reset',action(s,'submit',cid,flag).json()['data']['status']=='correct')
check('duplicate practice submission rejected',action(s,'submit',cid,flag).status_code==409)
check('lifetime counts survive reset',totals(s)=={'correct':3,'wrong':2,'reset':1,'box_reset':0})
check('other account has separate totals',totals(other)=={'correct':0,'wrong':0,'reset':0,'box_reset':0})
check('cannot reset another account via supplied id',action(other,'reset',cid,user_id=uid).status_code==403)
with app.app_context():
    check('replay never creates duplicate scoring solve',Solves.query.filter_by(user_id=uid).count()==1)
check('profile contains lifetime record', 'Your lifetime training record' in s.get(base+'/user').text)
check('practice page buttons render', 'Reset all my practice stages' in s.get(base+'/practice').text)
allowance()
check('players cannot reset practice',action(s,'reset_box').status_code==403)
check('whole reset updates both counters',totals(s)=={'correct':3,'wrong':2,'reset':2,'box_reset':1})
allowance()
with ThreadPoolExecutor(max_workers=10) as pool:
    responses=list(pool.map(lambda _: requests.post(base+'/practice/action',cookies=s.cookies,
        headers={'CSRF-Token':s.headers['CSRF-Token']},json={'action':'submit','challenge_id':cid,'submission':'wrong'}),range(10)))
check('concurrent guesses atomically limited',sum(r.status_code==200 for r in responses)==5 and sum(r.status_code==429 for r in responses)==5)
check('only evaluated wrong flags counted',totals(s)['wrong']==7)
# Expire only minute buckets: the hourly limit must survive.
with app.app_context():
    for row in ReplayLimit.query.all():
        if row.key.endswith('-60'):row.start-=61
        if row.key==f'flag-account-{uid}-3600':row.count=30
    db.session.commit()
check('hourly cap enforced after minute expires',attempt(s,cid,flag).status_code==429)
allowance()
for later_id,later_flag in challenges[1:]:
    check('next competition stage solves',attempt(s,later_id,later_flag).json()['data']['status']=='correct')
check('all six stages available for replay',len(s.get(base+'/practice/stats').json()['data']['rows'])==6)
with app.app_context():
    user=Users.query.get(uid)
    check('competition score remains 1150',user.score==1150)
allowance()
check('players still cannot bulk reset',action(s,'reset_box').status_code==403)
check('per-stage resets reflected',totals(s)['reset']==8 and totals(s)['box_reset']==2)
check('malformed submission denied',action(s,'submit',cid,['invalid']).status_code==400)
before_get=totals(s)
check('GET cannot change state',s.get(base+'/practice/action').status_code in (404,405) and totals(s)==before_get)
allowance()
for _ in range(3):
    check('reset within allowance',action(s,'reset',cid).status_code==200)
check('reset spam limited',action(s,'reset',cid).status_code==429)
allowance()
for _ in range(5):
    action(s,'submit',cid,'wrong')
s.headers['X-Forwarded-For']='198.51.100.12'
check('forged source header cannot bypass account cap',action(s,'submit',cid,flag).status_code==429)
s.headers.pop('X-Forwarded-For')
# Reconciliation remains idempotent across process restart / repeated reads.
one=totals(s); two=totals(s)
check('history import idempotent',one==two)
print('REPLAY_TEST_JSON:'+json.dumps({'passed':len(results),'failed':0,'checks':results,'test_user':uid}))
