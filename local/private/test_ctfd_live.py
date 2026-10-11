import json,re,secrets,sys,time
from html.parser import HTMLParser
import requests
sys.path.insert(0,'/opt/CTFd')
from CTFd import create_app
from CTFd.models import Challenges,Hints,Users,db
from CTFd.cache import cache

checks=[]
def check(name,condition):
    assert condition,name
    checks.append({'test':name,'status':'passed'})
class Form(HTMLParser):
    nonce=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('name')=='nonce': self.nonce=a.get('value')
app=create_app()
base='http://127.0.0.1:8000'
name='full-test-'+secrets.token_hex(4)
password=secrets.token_hex(20)
s=requests.Session()
page=s.get(base+'/register',timeout=20)
form=Form();form.feed(page.text)
r=s.post(base+'/register',data=dict(name=name,email=name+'@example.test',password=password,nonce=form.nonce),timeout=20)
check('Player registration through HTTP',r.status_code==200 and '/register' not in r.url)
with app.app_context():
    user=Users.query.filter_by(name=name).one(); user.hidden=True; db.session.commit(); uid=user.id
    rows=Challenges.query.order_by(Challenges.id).all()
    records=[{'id':c.id,'name':c.name,'value':c.value,'hints':[(h.id,h.cost) for h in Hints.query.filter_by(challenge_id=c.id)]} for c in rows]
check('Six challenges and 1150 available points',len(records)==6 and sum(c['value'] for c in records)==1150)
html=s.get(base+'/challenges',timeout=20).text
csrf=re.search(r"['\"]?csrfNonce['\"]?\s*:\s*['\"]([^'\"]+)",html)[1]
headers={'CSRF-Token':csrf}
flags=json.load(open('/organizer/challenges.json'))
def attempt(cid,flag):
    return s.post(base+'/api/v1/challenges/attempt',json={'challenge_id':cid,'submission':flag},headers=headers,timeout=20)
denied=s.get(base+'/api/v1/configs',timeout=20,allow_redirects=False)
check('Player cannot access admin configuration API',denied.status_code in (401,403) or (denied.status_code==302 and '/login' in denied.headers.get('Location','')))
locked=s.get(base+f"/api/v1/challenges/{records[-1]['id']}",timeout=20)
check('Final challenge locked before prerequisites',locked.status_code==403)
locked_attempt=attempt(records[-1]['id'],flags[-1]['flag'])
check('Correct final flag cannot bypass prerequisites',locked_attempt.status_code==403)
expected=0
for i,(c,f) in enumerate(zip(records,flags),1):
    # Keep deliberate wrong guesses below CTFd's normal anti-bruteforce limit.
    if i>1: time.sleep(13)
    cid=c['id']
    check(f'Stage {i}: unlocked after preceding solve',s.get(base+f'/api/v1/challenges/{cid}',timeout=20).status_code==200)
    check(f'Stage {i}: wrong flag rejected',attempt(cid,'FLAG{wrong_answer}').json()['data']['status']=='incorrect')
    check(f'Stage {i}: flag case enforced',attempt(cid,f['flag'].lower()).json()['data']['status']=='incorrect')
    check(f'Stage {i}: correct flag accepted',attempt(cid,f['flag']).json()['data']['status']=='correct')
    check(f'Stage {i}: duplicate does not score',attempt(cid,f['flag']).json()['data']['status']=='already_solved')
    expected+=c['value']
    for hid,cost in c['hints']:
        r=s.post(base+'/api/v1/unlocks',json={'target':hid,'type':'hints'},headers=headers,timeout=20)
        check(f'Stage {i}: hint {hid} purchase',r.json().get('success') is True)
        check(f'Stage {i}: hint {hid} content visible',bool(s.get(base+f'/api/v1/hints/{hid}',timeout=20).json()['data'].get('content')))
        expected-=cost
    with app.app_context():
        check(f'Stage {i}: cumulative score and hint charges',db.session.get(Users,uid).get_score(admin=True)==expected)
    print(f'Stage {i} passed; cumulative score {expected}',flush=True)
print('RESULT_JSON:'+json.dumps({'status':'passed','checks':checks,'test_user':name,'user_id':uid,'score_after_all_hints':expected,'maximum_score':1150}))
