"""Local preview, private configuration and per-team verifier credentials."""
import argparse
import hashlib
import json
import secrets
import sqlite3
import threading
from pathlib import Path
from flask import Flask, send_from_directory
from waitress import serve
from ctf.portal import create_app as portal_app
from ctf.verifier import create_app as verifier_app

ROOT = Path(__file__).resolve().parent

def settings():
    path = ROOT / 'runtime/settings.json'
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(dict(portal_secret=secrets.token_hex(32), verifier_secret=secrets.token_hex(32))))
    return json.loads(path.read_text())

def apps():
    cfg = settings()
    archive = Flask('archive', static_folder=None)
    @archive.get('/')
    def index():
        return send_from_directory(ROOT/'build/stage1', 'index.html')
    @archive.get('/<path:name>')
    def file(name):
        return send_from_directory(ROOT/'build/stage1', name)
    portal = portal_app(dict(SECRET_KEY=cfg['portal_secret'], DATA_DIR=ROOT/'build/portal', SESSION_COOKIE_NAME='northstar_portal'))
    verifier = verifier_app(dict(SECRET_KEY=cfg['verifier_secret'], ANSWER_FILE=ROOT/'build/verifier/answer.json', DATABASE=ROOT/'runtime/verifier.sqlite', SESSION_COOKIE_NAME='northstar_verifier'))
    return archive, portal, verifier

def issue_team(database, team, rotate=False):
    if not team or len(team) > 64:
        raise ValueError('Team ID must contain 1–64 characters')
    token = secrets.token_urlsafe(32)
    with sqlite3.connect(database) as db:
        existing = db.execute('SELECT 1 FROM teams WHERE id=?', (team,)).fetchone()
        if existing and not rotate:
            raise ValueError('Team exists; use --rotate to invalidate its previous token')
        db.execute('INSERT INTO teams(id,token_hash) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash,enabled=1', (team,hashlib.sha256(token.encode()).hexdigest()))
    return token

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preview')
    issue = sub.add_parser('issue-team')
    issue.add_argument('team')
    issue.add_argument('--rotate', action='store_true')
    issue.add_argument('--database', type=Path)
    revoke = sub.add_parser('revoke-team')
    revoke.add_argument('team')
    revoke.add_argument('--database', type=Path)
    args = parser.parse_args()
    if args.command == 'preview':
        services = apps()
        for app, port in zip(services[:2], (8081,8083)):
            threading.Thread(target=serve, args=(app,), kwargs=dict(host='127.0.0.1',port=port), daemon=True).start()
        print('Archive: http://127.0.0.1:8081 | Portal: http://127.0.0.1:8083 | Verifier: http://127.0.0.1:8443', flush=True)
        print('Local HTTP preview. CTFd scoring and Linux SSH use the deployment stacks.', flush=True)
        serve(services[2], host='127.0.0.1', port=8443)
    else:
        database = args.database
        if database is None:
            apps()  # Create schema on first use.
            database = ROOT/'runtime/verifier.sqlite'
        if args.command == 'issue-team':
            print(issue_team(database, args.team, args.rotate))
        else:
            with sqlite3.connect(database) as db:
                changed = db.execute('UPDATE teams SET enabled=0 WHERE id=?', (args.team,)).rowcount
            print(f'Revoked {changed} team(s). Existing sessions are denied on their next request.')
