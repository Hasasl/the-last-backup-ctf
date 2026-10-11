"""Run inside the pinned CTFd container. Creates one isolated local event."""
import json
import os
import sys
sys.path.insert(0, '/opt/CTFd')
from CTFd import create_app
from CTFd.models import Admins, Challenges, Flags, Hints, Pages, Users, db
from CTFd.utils import get_config, set_config
from CTFd.cache import cache

app = create_app()
with app.app_context():
    marker = 'last_backup_stage1_bootstrap'
    challenge = json.load(open('/bootstrap/challenge.json'))
    if get_config(marker):
        assert Challenges.query.count() == 1, 'Unexpected challenge count; inspect manually.'
        print('Stage 1 is already initialized. Scores and accounts preserved.')
        sys.exit(0)
    if get_config('setup') or Users.query.count() or Challenges.query.count():
        raise SystemExit('Existing event detected. Refusing to replace it.')
    admin = Admins(name=os.environ['ADMIN_NAME'], email=os.environ['ADMIN_EMAIL'],
                   password=os.environ['ADMIN_PASSWORD'], hidden=True, verified=True)
    row = Challenges(name=challenge['name'], category='OSINT', value=100,
                     type='standard', state='visible', max_attempts=0,
                     description=challenge['description'])
    db.session.add_all([admin, row])
    db.session.flush()
    db.session.add(Flags(challenge_id=row.id, type='static',
                         content=challenge['flag'], data='case_sensitive'))
    for hint in challenge['hints']:
        db.session.add(Hints(challenge_id=row.id, content=hint['content'], cost=hint['cost']))
    db.session.add(Pages(route='index', title='The Last Backup', draft=False,
                        content='# The Last Backup\n\n## The Missing Employee\n\n'
                        'Investigate Northstar Labs and recover Maya’s missing record. '
                        'One OSINT challenge. 100 points. Two optional hints.\n\n'
                        '[Register to play](/register) · [Open challenges](/challenges)\n\n'
                        'Use a separate player account; the organizer account manages the event.'))
    db.session.commit()
    for key, value in dict(ctf_name='The Last Backup',
                           ctf_description='Stage 1 — The Missing Employee',
                           user_mode='users', ctf_theme='core',
                           challenge_visibility='private', registration_visibility='public',
                           account_visibility='public', score_visibility='public',
                           verify_emails=False, setup=True).items():
        set_config(key, value)
    set_config(marker, True)
    cache.clear()
    print('Created exactly one challenge with one static flag and two hints.')
