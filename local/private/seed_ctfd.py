"""Seed a NEW CTFd event using an organizer access token from the environment.

Uses hidden records until each flag, hint and prerequisite is saved. Later binary
handouts are deliberately issued manually, avoiding direct-download bypasses.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

def api(base, token, method, path, data=None):
    request = Request(base.rstrip('/')+'/api/v1'+path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Authorization':'Token '+token,'Content-Type':'application/json'}, method=method)
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get('success'):
        raise RuntimeError(f'CTFd rejected {method} {path}')
    return result['data']

def seed(base, token, challenges, urls, call=api):
    existing = call(base,token,'GET','/challenges')
    names = {c['name'] for c in existing}
    if names.intersection(c['name'] for c in challenges):
        raise RuntimeError('Matching challenges already exist. Refusing duplicates; inspect the existing event before retrying.')
    previous, created = None, []
    for c in challenges:
        description = c['description']
        for key, value in urls.items():
            description = description.replace('{'+key+'}', value)
        record = dict(name=c['name'], category=c['category'], description=description,
                      value=c['value'], type='standard', state='hidden', max_attempts=0)
        challenge = call(base,token,'POST','/challenges',record)
        cid = challenge['id']
        call(base,token,'POST','/flags',dict(challenge=cid, type='static', content=c['flag'], data='case_sensitive'))
        for hint in c['hints']:
            call(base,token,'POST','/hints',dict(challenge=cid, content=hint['content'], cost=hint['cost']))
        if previous:
            call(base,token,'PATCH',f'/challenges/{cid}',dict(requirements={'prerequisites':[previous]}))
        created.append(cid)
        previous = cid
    for cid in created:
        call(base,token,'PATCH',f'/challenges/{cid}',dict(state='visible'))
    return created

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--split-stage5', action='store_true')
    parser.add_argument('--archive-url', default='http://192.168.77.20:8081')
    parser.add_argument('--portal-url', default='http://192.168.77.20:8083')
    parser.add_argument('--verifier-url', default='https://192.168.77.40')
    args = parser.parse_args()
    filename = 'challenges-split5.json' if args.split_stage5 else 'challenges.json'
    challenges = json.loads((Path(__file__).resolve().parents[1]/'build/organizer'/filename).read_text(encoding='utf-8'))
    urls = dict(archive_url=args.archive_url,portal_url=args.portal_url,verifier_url=args.verifier_url)
    print('Created challenge IDs:', seed(args.url,os.environ['CTFD_TOKEN'],challenges,urls))
