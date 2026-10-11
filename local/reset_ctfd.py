"""Reset CTFd progress. Runs INSIDE the ctfd container (piped on stdin).

Env:
  RESET_MODE  scores  = delete solves, wrong attempts, awards, hint purchases
                        (keeps player accounts, challenges, flags, hints, pages)
              players = scores, PLUS delete all non-admin player accounts
  RESET_DRY   1 = report only, change nothing
Challenges, flags, hints, pages, theme and the admin account are never touched.
"""
import json, os, sys
sys.path.insert(0, '/opt/CTFd')
from sqlalchemy import bindparam, inspect, text
from CTFd import create_app
from CTFd.models import db

mode = os.environ.get('RESET_MODE', 'scores')
dry = os.environ.get('RESET_DRY', '') == '1'
if mode not in ('scores', 'players'):
    raise SystemExit('RESET_MODE must be scores or players')
PROGRESS = ['solves', 'fails', 'submissions', 'awards', 'unlocks', 'tracking']

app = create_app()
with app.app_context():
    # Preserve lifetime flags before an organizer clears competition progress.
    from CTFd.plugins.northstar_replay import sync_history
    sync_history()
    names = set(inspect(db.engine).get_table_names())
    def count(sql, **kw):
        return db.session.execute(text(sql), kw).scalar()
    out = {'mode': mode, 'dry_run': dry, 'cleared': {}, 'remaining': {}}
    for t in PROGRESS:
        if t in names:
            out['cleared'][t] = count('SELECT COUNT(*) FROM ' + t)
    ids = []
    if mode == 'players' and 'users' in names:
        ids = [r[0] for r in db.session.execute(text("SELECT id FROM users WHERE type='user'"))]
        out['cleared']['users'] = len(ids)
    if not dry:
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        for t in PROGRESS:  # solves/fails first: they are child rows of submissions
            if t in names:
                db.session.execute(text('DELETE FROM ' + t))
        if ids:
            insp = inspect(db.engine)
            for t in sorted(names):
                if t == 'users':
                    continue
                for fk in insp.get_foreign_keys(t):
                    if fk['referred_table'] == 'users' and fk['referred_columns'] == ['id']:
                        for col in fk['constrained_columns']:
                            db.session.execute(text(f'DELETE FROM {t} WHERE {col} IN :ids').bindparams(
                                bindparam('ids', expanding=True)), {'ids': ids})
            db.session.execute(text("DELETE FROM users WHERE type='user'"))
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        db.session.commit()
        from CTFd.cache import cache
        cache.clear()
    for t in PROGRESS:
        if t in names:
            out['remaining'][t] = count('SELECT COUNT(*) FROM ' + t)
    out['remaining']['users_total'] = count('SELECT COUNT(*) FROM users')
    out['kept'] = {'challenges': count('SELECT COUNT(*) FROM challenges'),
                   'flags': count('SELECT COUNT(*) FROM flags'),
                   'hints': count('SELECT COUNT(*) FROM hints'),
                   'admins': count("SELECT COUNT(*) FROM users WHERE type='admin'")}
    print('RESET_JSON:' + json.dumps(out, sort_keys=True))
