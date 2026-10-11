"""Initialize this new event, then use the real HTTP API to seed all stages."""
import json, os, re, sys, time
import requests
sys.path.insert(0, '/opt/CTFd')
sys.path.insert(0, '/bootstrap')
from CTFd import create_app
from CTFd.models import Admins, Challenges, Pages, Users, db
from CTFd.utils import get_config, set_config
from CTFd.cache import cache
from seed_ctfd import seed

app = create_app()
with app.app_context():
    if get_config('last_backup_full_ready'):
        assert Challenges.query.count() == 6
        print('Full event already initialized. Existing progress preserved.')
        sys.exit(0)
    if not get_config('setup'):
        assert Users.query.count() == 0 and Challenges.query.count() == 0
        db.session.add(Admins(name=os.environ['ADMIN_NAME'],email=os.environ['ADMIN_EMAIL'],password=os.environ['ADMIN_PASSWORD'],hidden=True,verified=True))
        db.session.add(Pages(route='index',title='The Last Backup',draft=False,content='# The Last Backup\n\nInvestigate Northstar Labs through six linked stages: OSINT, steganography, web evidence, cryptography, digital forensics and Linux investigation. **1,150 points.**\n\n[Register to play](/register) · [Open challenges](/challenges)\n\nComplete stages in order. Ask your organizer for the forensic image after Stage 4, then SSH credentials and a verifier token after Stage 5. All evidence is fictional.'))
        db.session.commit()
        for k,v in dict(ctf_name='The Last Backup — Full Project',ctf_description='Six stages · 1,150 points',user_mode='users',ctf_theme='core',challenge_visibility='private',registration_visibility='public',account_visibility='public',score_visibility='public',verify_emails=False,setup=True).items():
            set_config(k,v)
        cache.clear()

base = 'http://127.0.0.1:8000'
s = requests.Session()
page = s.get(base+'/login',timeout=30)
nonce = re.search(r'name="nonce"[^>]*value="([^"]+)"',page.text)
if not nonce:
    from html.parser import HTMLParser
    class Nonce(HTMLParser):
        value = None
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if a.get('name')=='nonce': self.value=a.get('value')
    f=Nonce(); f.feed(page.text); token=f.value
else: token=nonce[1]
assert token
r=s.post(base+'/login',data=dict(name=os.environ['ADMIN_NAME'],password=os.environ['ADMIN_PASSWORD'],nonce=token),timeout=30)
assert '/login' not in r.url
html=s.get(base+'/admin/challenges',timeout=30).text
csrf=re.search(r"['\"]?csrfNonce['\"]?\s*:\s*['\"]([^'\"]+)",html)[1]
def api(base,token,method,path,data=None):
    r=s.request(method,base+'/api/v1'+path,json=data,headers={'CSRF-Token':csrf},timeout=30)
    r.raise_for_status()
    value=r.json()
    assert value.get('success'), value
    return value['data']
challenges=json.load(open('/organizer/challenges.json'))
ids=seed(base,'',challenges,dict(archive_url='http://localhost:8081',portal_url='http://localhost:8083',verifier_url='http://localhost:8443'),call=api)
with app.app_context():
    set_config('last_backup_full_ready',True)
    cache.clear()
print(json.dumps({'status':'passed','challenge_ids':ids,'points':sum(c['value'] for c in challenges),'method':'live CTFd HTTP API'}))
