"""Exercise the public loopback endpoints and actual downloaded evidence."""
import hashlib,http.cookiejar,json,re,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.error import HTTPError
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.solve import extract_png,recover_fat,timeline
from ctf.cipher import transform
root=Path(__file__).resolve().parents[1]
checks=[]
def check(name,condition):
    assert condition,name
    checks.append({'test':name,'status':'passed'})
class Client:
    def __init__(self): self.opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(self,url,data=None):
        try:r=self.opener.open(Request(url,data=urlencode(data).encode() if data is not None else None),timeout=15)
        except HTTPError as e:r=e
        return r.status,r.read(),dict(r.headers)
def csrf(body):return re.search(rb'name="csrf" value="([^"]+)"',body)[1].decode()
a=Client();p=Client();other=Client();v=Client()
archive='http://localhost:8081';portal='http://localhost:8083';verifier='http://localhost:8443'
check('CTFd homepage responds',a.get('http://localhost:8001')[0]==200)
check('OSINT unique corroborated notice serves Stage 1 flag',b'FLAG{st01_' in a.get(archive+'/notice-062.html')[1])
for path in ('/private/challenge.json','/build/organizer/challenges.json','/northstar_evidence.img','/.env'):
    check('Archive rejects '+path,a.get(archive+path)[0]==404)
status,png,_=a.get(archive+'/event-original.png')
check('Original PNG downloadable',status==200)
download=root/'test-results/downloaded-event.png';download.write_bytes(png)
note=extract_png(download)
check('Stage 2 payload recovered from HTTP download','FLAG{st02_' in note and '127.0.0.1:8083' in note)
check('Stage 3 early attachment denied',p.get(portal+'/attachments/elias.enc.txt')[0]==403)
check('Stage 3 health',p.get(portal+'/health')[0]==200)
status,body,headers=p.get(portal)
check('Portal security headers',headers.get('X-Frame-Options')=='DENY' and headers.get('X-Content-Type-Options')=='nosniff')
check('Portal missing CSRF rejected',p.get(portal+'/review',{'transaction':'TX-217','audit':'AUD-217'})[0]==400)
check('Portal wrong evidence rejected',p.get(portal+'/review',{'csrf':csrf(body),'transaction':'TX-000','audit':'AUD-000'})[0]==400)
status,body,_=p.get(portal+'/review',{'csrf':csrf(body),'transaction':'TX-217','audit':'AUD-217'})
check('Correct evidence releases Stage 3 flag',status==200 and b'FLAG{st03_' in body)
check('Independent session remains locked',other.get(portal+'/attachments/elias.enc.txt')[0]==403)
status,cipher,_=p.get(portal+'/attachments/elias.enc.txt')
check('Cipher handover released',status==200)
check('Training memo released',p.get(portal+'/attachments/training-memo.txt')[0]==200)
plain=transform(cipher.decode(),decrypt=True)
check('Stage 4 cipher solves','FLAG{st04_' in plain)
img=root/'build/handouts/northstar_evidence.img'
check('Stage 4 checksum matches Stage 5 image',hashlib.sha256(img.read_bytes()).hexdigest() in plain)
files=recover_fat(img);evidence=timeline(files)
check('Stage 5 deleted note recovered','FLAG{st05_' in files['_ANDOVER.TXT'])
check('Stage 5 timeline correct',evidence['service']=='mn-sync' and evidence['start'].endswith('02:17:00Z') and evidence['end'].endswith('02:34:00Z'))
check('Stage 5 manifest checksum matches Stage 6',evidence['manifest_sha256']==hashlib.sha256((root/'build/linux/manifests/R17.sha256').read_bytes()).hexdigest())
status,body,_=v.get(verifier)
check('Verifier responds',status==200)
check('Verifier rejects invalid token',v.get(verifier,{'csrf':csrf(body),'token':'invalid-token'})[0]==403)
status,body,_=v.get(verifier)
token=(root/'local/private/ui-verifier-token.txt').read_text().strip()
status,body,_=v.get(verifier,{'csrf':csrf(body),'token':token})
check('Verifier token login',status==200 and b'release_id' in body)
bad=dict(csrf=csrf(body),release_id='wrong',route_id='wrong',service='wrong',event_id='wrong')
check('Verifier wrong answer rejected',v.get(verifier+'/verify',bad)[0]==400)
good=dict(csrf=csrf(body),release_id='R17',route_id='EXIT-04',service='mn-sync',event_id='EVT-024')
status,body,_=v.get(verifier+'/verify',good)
check('Verifier correct answer returns final flag',status==200 and b'FLAG{st06_' in body)
check('Verifier completion survives another request',b'FLAG{st06_' in v.get(verifier+'/verify')[1])
for _ in range(3):v.get(verifier+'/verify',bad)
check('Deployed verifier enforces five attempts per minute',v.get(verifier+'/verify',bad)[0]==429)
urls=['http://localhost:8001/',archive+'/',portal+'/',verifier+'/']
def visit(url):
    start=time.perf_counter();status,_,_=Client().get(url)
    return {'url':url,'status':status,'seconds':round(time.perf_counter()-start,3)}
with ThreadPoolExecutor(max_workers=4) as pool:timings=list(pool.map(visit,urls*4))
check('Four concurrent clients: all 16 pages succeed',all(r['status']==200 for r in timings))
check('Four concurrent clients: every page under three seconds',max(r['seconds'] for r in timings)<3)
report={'status':'passed','checks':checks,'page_timings':timings,'maximum_seconds':max(r['seconds'] for r in timings)}
(root/'test-results/ui-live-http.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'status':'passed','checks':len(checks),'maximum_seconds':report['maximum_seconds']}))
