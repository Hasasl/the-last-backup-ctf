import os
from .portal import create_app as portal_app
from .verifier import create_app as verifier_app

service = os.environ['SERVICE']
config = dict(SECRET_KEY=os.environ['SECRET_KEY'],
              SESSION_COOKIE_SECURE=service == 'verifier',
              SESSION_COOKIE_NAME='northstar_' + service)
if service == 'portal':
    app = portal_app({**config, 'DATA_DIR': '/data', 'GUARD_DATABASE': '/state/portal-guard.sqlite'})
elif service == 'verifier':
    app = verifier_app({**config, 'ANSWER_FILE': '/data/answer.json', 'DATABASE': '/state/verifier.sqlite'})
else:
    raise ValueError('Unknown service')
