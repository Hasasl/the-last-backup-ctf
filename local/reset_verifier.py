"""Reset verifier progress. Runs INSIDE the verifier container (piped on stdin).

Env:
  RESET_TEAM   team id to reset; empty = every team
  RESET_DRY    1 = report only, change nothing
Teams and tokens are kept, so issued tokens keep working.
"""
import json, os, sqlite3

DB = os.environ.get('RESET_DB', '/state/verifier.sqlite')
team = os.environ.get('RESET_TEAM', '').strip()
dry = os.environ.get('RESET_DRY', '') == '1'

db = sqlite3.connect(DB, timeout=15)
db.execute('BEGIN IMMEDIATE')
out = {'team': team or '(all)', 'dry_run': dry, 'cleared': {}, 'remaining': {}}
for table in ('completions', 'attempts'):
    if team:
        n = db.execute(f'SELECT COUNT(*) FROM {table} WHERE team=?', (team,)).fetchone()[0]
        if not dry:
            db.execute(f'DELETE FROM {table} WHERE team=?', (team,))
    else:
        n = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        if not dry:
            db.execute(f'DELETE FROM {table}')
    out['cleared'][table] = n
n = db.execute('SELECT COUNT(*) FROM logins').fetchone()[0]
if not dry:
    db.execute('DELETE FROM logins')  # sign-in throttle is per IP, not per team
out['cleared']['logins'] = n
if team:
    out['team_exists'] = bool(db.execute('SELECT 1 FROM teams WHERE id=?', (team,)).fetchone())
db.commit()
for table in ('completions', 'attempts'):
    q = f'SELECT COUNT(*) FROM {table}' + (' WHERE team=?' if team else '')
    out['remaining'][table] = db.execute(q, (team,) if team else ()).fetchone()[0]
out['teams_kept'] = db.execute('SELECT COUNT(*) FROM teams').fetchone()[0]
print('RESET_JSON:' + json.dumps(out, sort_keys=True))
