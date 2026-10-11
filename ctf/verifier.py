import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path
from flask import Flask, redirect, render_template, request, session, url_for
from .common import harden

def create_app(config):
    app = Flask(__name__)
    app.config.update(config)
    harden(app)
    private = json.loads(Path(app.config['ANSWER_FILE']).read_text())
    db_path = Path(app.config['DATABASE'])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect():
        db = sqlite3.connect(db_path, timeout=15)
        db.execute('PRAGMA journal_mode=WAL')
        return db

    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS teams (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, enabled INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS attempts (team TEXT NOT NULL, at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS attempts_team_at ON attempts(team, at);
        CREATE TABLE IF NOT EXISTS completions (team TEXT PRIMARY KEY, at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS logins (ip TEXT NOT NULL, at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS logins_ip_at ON logins(ip, at);
        ''')

    def team_active():
        team = session.get('team')
        with connect() as db:
            return team if db.execute('SELECT 1 FROM teams WHERE id=? AND enabled=1', (team,)).fetchone() else None

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.route('/', methods=['GET', 'POST'])
    def index():
        message, status = None, 200
        if request.method == 'POST':
            now = time.time()
            ip = request.remote_addr or 'local'
            with connect() as db:
                db.execute('BEGIN IMMEDIATE')
                count = db.execute('SELECT COUNT(*) FROM logins WHERE ip=? AND at>?', (ip, now-60)).fetchone()[0]
                if count >= 10:
                    message, status = 'Too many sign-in attempts. Wait one minute.', 429
                else:
                    db.execute('INSERT INTO logins VALUES (?, ?)', (ip, now))
                    token_hash = hashlib.sha256(request.form.get('token', '').strip().encode()).hexdigest()
                    row = db.execute('SELECT id FROM teams WHERE token_hash=? AND enabled=1', (token_hash,)).fetchone()
                    if row:
                        session.clear()
                        session['team'] = row[0]
                        session.permanent = True
                        return redirect(url_for('verify'))
                    message, status = 'Access token not recognized.', 403
                db.execute('DELETE FROM logins WHERE at<?', (now-3600,))
        if request.method == 'GET' and team_active():
            return redirect(url_for('verify'))
        return render_template('login.html', title='Backup Verification Console', message=message), status

    @app.route('/verify', methods=['GET', 'POST'])
    def verify():
        team = team_active()
        if not team:
            return redirect(url_for('index'))
        message, flag, status = None, None, 200
        now = time.time()
        if request.method == 'POST':
            fields = ('release_id', 'route_id', 'service', 'event_id')
            answer = {field: request.form.get(field, '').strip() for field in fields}
            with connect() as db:
                db.execute('BEGIN IMMEDIATE')
                count = db.execute('SELECT COUNT(*) FROM attempts WHERE team=? AND at>?', (team, now-60)).fetchone()[0]
                hourly = db.execute('SELECT COUNT(*) FROM attempts WHERE team=? AND at>?', (team, now-3600)).fetchone()[0]
                if hourly >= 30:
                    message, status = 'Thirty attempts used. Wait until your hourly allowance renews.', 429
                elif count >= 5:
                    message, status = 'Five attempts used. Wait one minute before retrying.', 429
                else:
                    db.execute('INSERT INTO attempts VALUES (?, ?)', (team, now))
                    # Compare all four fields as one value; never execute user input.
                    correct = secrets.compare_digest(json.dumps(answer, sort_keys=True).encode(), json.dumps(private['answer'], sort_keys=True).encode())
                    if correct:
                        db.execute('INSERT OR IGNORE INTO completions VALUES (?, ?)', (team, now))
                    else:
                        message, status = 'Evidence does not match the trusted recovery record.', 400
                db.execute('DELETE FROM attempts WHERE at<?', (now-3600,))
        with connect() as db:
            if db.execute('SELECT 1 FROM completions WHERE team=?', (team,)).fetchone():
                flag = private['flag']
        return render_template('verify.html', title='Backup Verification Console', team=team,
                               message=message, flag=flag), status

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    return app
