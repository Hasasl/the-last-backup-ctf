"""Personal practice runs and durable throttling for CTFd 3.7.7 / MariaDB.

Competition solves stay in CTFd. Practice never awards points or deletes them.
All mutations for one account are serialized across Gunicorn workers.
"""
import hashlib
import math
import time
from contextlib import contextmanager
from functools import wraps

from flask import Blueprint, abort, jsonify, make_response, render_template, request
from sqlalchemy import text
from CTFd.models import db, Challenges, Submissions, Solves
from CTFd.plugins.challenges import get_chal_class
from CTFd.utils.user import get_current_user
from CTFd.utils.decorators import authed_only, during_ctf_time_only, require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.dates import ctf_paused


class ReplayEvent(db.Model):
    __tablename__ = 'northstar_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    challenge_id = db.Column(db.Integer, nullable=True)
    kind = db.Column(db.String(24), nullable=False)
    source_id = db.Column(db.Integer, unique=True, nullable=True)
    at = db.Column(db.Float, nullable=False, default=time.time)


class ReplayRun(db.Model):
    __tablename__ = 'northstar_runs'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    challenge_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False, default=1)
    complete = db.Column(db.Boolean, nullable=False, default=False)


class ReplayLimit(db.Model):
    __tablename__ = 'northstar_limits'
    key = db.Column(db.String(100), primary_key=True)
    start = db.Column(db.Float, nullable=False)
    count = db.Column(db.Integer, nullable=False)


@contextmanager
def locks(names):
    # A dedicated connection keeps advisory locks through CTFd's own commits.
    conn = db.engine.connect()
    acquired = []
    try:
        for name in sorted(set(names)):
            if conn.execute(text('SELECT GET_LOCK(:name, 5)'), {'name': name}).scalar() != 1:
                abort(503, 'Another action is running. Please retry shortly.')
            acquired.append(name)
        yield
    finally:
        for name in reversed(acquired):
            conn.execute(text('SELECT RELEASE_LOCK(:name)'), {'name': name})
        conn.close()


def account_lock(user):
    return 'ns-account-' + str(user.account_id)


def sync_history(user_id=None):
    # INSERT IGNORE makes migration/reconciliation idempotent across workers.
    clause = ' AND s.user_id = :uid' if user_id is not None else ''
    db.session.execute(text('''INSERT IGNORE INTO northstar_events
        (user_id, challenge_id, kind, source_id, at)
        SELECT s.user_id, s.challenge_id,
        CASE WHEN s.type = 'correct' THEN 'correct' ELSE 'wrong' END,
        s.id, UNIX_TIMESTAMP(s.date)
        FROM submissions s WHERE s.type IN ('correct', 'incorrect')''' + clause), {'uid': user_id})
    db.session.commit()


def throttle(user, action='flag'):
    now = time.time()
    # Only the trusted socket address is used; forged forwarding headers cannot
    # create new buckets. REVERSE_PROXY remains disabled in compose.local.yml.
    ip = hashlib.sha256((request.remote_addr or 'local').encode()).hexdigest()[:32]
    limits = [(f'{action}-account-{user.account_id}', 60, 5 if action == 'flag' else 3),
              (f'{action}-account-{user.account_id}', 3600, 30 if action == 'flag' else 20),
              (f'{action}-ip-{ip}', 60, 60),
              (f'{action}-ip-{ip}', 3600, 300)]
    with locks(['ns-ip-' + ip]):
        # Authentication may have opened a REPEATABLE READ snapshot before
        # waiting for the lock. Refresh it to see the previous worker's commit.
        db.session.rollback()
        rows, retry = [], 0
        for key, window, maximum in limits:
            key += '-' + str(window)
            row = ReplayLimit.query.get(key)
            if row is None:
                row = ReplayLimit(key=key, start=now, count=0)
                db.session.add(row)
            elif now >= row.start + window:
                row.start, row.count = now, 0
            if row.count >= maximum:
                retry = max(retry, math.ceil(row.start + window - now))
            rows.append(row)
        if not retry:
            for row in rows:
                row.count += 1
        db.session.commit()
    if retry:
        response = jsonify(success=True, data={'status': 'ratelimited',
            'message': f'Too many attempts. Try again in {retry} seconds.', 'retry_after': retry})
        response.status_code = 429
        response.headers['Retry-After'] = str(retry)
        return response


def event(user, kind, challenge_id=None):
    db.session.add(ReplayEvent(user_id=user.id, kind=kind, challenge_id=challenge_id))


def stats():
    user = get_current_user()
    if not user:
        return None
    sync_history(user.id)
    events = ReplayEvent.query.filter_by(user_id=user.id).all()
    totals = {k: sum(e.kind == k for e in events) for k in ('correct', 'wrong', 'reset', 'box_reset')}
    solved = {s.challenge_id for s in Solves.query.filter_by(account_id=user.account_id).all()}
    runs = {r.challenge_id: r for r in ReplayRun.query.filter_by(user_id=user.id).all()}
    rows = []
    for challenge in Challenges.query.filter_by(state='visible').order_by(Challenges.id).all():
        # Practice becomes available only after the competition solve.
        if challenge.id not in solved:
            continue
        run = runs.get(challenge.id)
        rows.append(dict(id=challenge.id, name=challenge.name, run=run.number if run else 1,
                         complete=bool(run and run.complete),
                         **{k: sum(e.kind == k and e.challenge_id == challenge.id for e in events)
                            for k in ('correct', 'wrong', 'reset')}))
    return dict(totals=totals, rows=rows)


def load(app):
    with app.app_context(), locks(['ns-schema']):
        db.create_all()
        sync_history()

    # Wrap the existing endpoint, retaining CTFd visibility, time, prerequisites,
    # max-attempt and scoring checks. Practice and competition share the limiter.
    from CTFd.api.v1.challenges import ChallengeAttempt
    original = ChallengeAttempt.post
    if not getattr(original, '_northstar', False):
        @wraps(original)
        def guarded(self, *args, **kwargs):
            user = get_current_user()
            if not user:
                return original(self, *args, **kwargs)
            with locks([account_lock(user)]):
                limited = throttle(user)
                if limited is not None:
                    return limited
                payload = request.get_json(silent=True) if request.is_json else request.form
                if not isinstance(payload, dict) and not hasattr(payload, 'get'):
                    abort(400)
                value = payload.get('submission')
                if not isinstance(value, str) or not value.strip() or len(value) > 512:
                    abort(400, 'Enter a flag of 1–512 characters.')
                response = original(self, *args, **kwargs)
                sync_history(user.id)
                return response
        guarded._northstar = True
        ChallengeAttempt.post = guarded

    bp = Blueprint('northstar_replay', __name__)

    @bp.route('/practice')
    @authed_only
    def practice():
        return render_template('northstar-practice.html', practice=stats())

    @bp.route('/practice/stats')
    @authed_only
    def statistics():
        return jsonify(success=True, data=stats())

    @bp.route('/practice/action', methods=['POST'])
    @authed_only
    @check_challenge_visibility
    @during_ctf_time_only
    @require_verified_emails
    def action():
        user = get_current_user()
        if ctf_paused():
            abort(403)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400)
        operation = data.get('action')
        # Resetting is an organizer-only operation (admin dashboard); players
        # can only submit practice flags.
        if operation != 'submit':
            abort(403)
        with locks([account_lock(user)]):
            limited = throttle(user, 'flag' if operation == 'submit' else 'reset')
            if limited is not None:
                return limited
            solved = {s.challenge_id for s in Solves.query.filter_by(account_id=user.account_id).all()}
            cid = data.get('challenge_id')
            if type(cid) is not int:
                abort(400)
            challenge = Challenges.query.filter_by(id=cid, state='visible').first_or_404()
            if cid not in solved:
                abort(403)
            run = ReplayRun.query.get((user.id, cid))
            if run is None:
                run = ReplayRun(user_id=user.id, challenge_id=cid, number=1, complete=False)
                db.session.add(run)
            if run.complete:
                return jsonify(success=True, data={'status': 'already_solved',
                    'message': 'Practice for this stage is already complete.'}), 409
            value = data.get('submission')
            if not isinstance(value, str) or not value.strip() or len(value) > 512:
                abort(400)
            correct, _ = get_chal_class(challenge.type).attempt(challenge, request)
            run.complete = correct
            event(user, 'correct' if correct else 'wrong', cid)
            db.session.commit()
            return jsonify(success=True, data={'status': 'correct' if correct else 'incorrect',
                'message': 'Correct flag. Practice completed; competition points stay unchanged.' if correct else 'Incorrect flag.'})

    app.register_blueprint(bp)

    # ---- Organizer-only reset (CTFd admin dashboard) -------------------------
    from CTFd.utils.decorators import admins_only
    from CTFd.cache import cache
    from CTFd.plugins import register_admin_plugin_menu_bar

    # Only challenge progress is cleared. Accounts, teams, challenges, flags,
    # hints, pages, awards, IP tracking and the lifetime flag ledger are kept.
    PROGRESS = ('solves', 'fails', 'submissions', 'unlocks', 'northstar_runs')

    def progress_tables():
        # CTFd keeps wrong attempts inside `submissions`, so `fails` may not be
        # a real table. Only touch tables that exist.
        from sqlalchemy import inspect
        existing = set(inspect(db.engine).get_table_names())
        return [t for t in PROGRESS if t in existing]

    def progress_counts():
        counts = dict.fromkeys(PROGRESS, 0)
        for t in progress_tables():
            counts[t] = db.session.execute(text('SELECT COUNT(*) FROM ' + t)).scalar()
        # Wrong attempts are stored as submissions of type 'incorrect'.
        if 'fails' not in progress_tables() and 'submissions' in progress_tables():
            counts['fails'] = db.session.execute(
                text("SELECT COUNT(*) FROM submissions WHERE type = 'incorrect'")).scalar()
        return counts

    admin_bp = Blueprint('northstar_admin_reset', __name__, template_folder='templates')

    @admin_bp.route('/admin/northstar-reset', methods=['GET', 'POST'])
    @admins_only
    def admin_reset():
        done = None
        error = None
        if request.method == 'POST':
            if request.form.get('confirm', '').strip() != 'RESET':
                error = 'Type RESET exactly to confirm.'
            else:
                with locks(['ns-admin-reset']):
                    db.session.rollback()
                    done = progress_counts()
                    db.session.execute(text('SET FOREIGN_KEY_CHECKS=0'))
                    try:
                        for t in progress_tables():  # solves/fails are child rows of submissions
                            db.session.execute(text('DELETE FROM ' + t))
                    finally:
                        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1'))
                    db.session.commit()
                cache.clear()
        return render_template('northstar_admin_reset.html', counts=progress_counts(),
                               done=done, error=error,
                               users=db.session.execute(text("SELECT COUNT(*) FROM users WHERE type='user'")).scalar())

    app.register_blueprint(admin_bp)
    register_admin_plugin_menu_bar('Reset Challenges', '/admin/northstar-reset')
    app.jinja_env.globals['northstar_stats'] = stats

    @app.after_request
    def private_responses(response):
        if request.path.startswith('/practice') or request.path == '/user':
            response.headers['Cache-Control'] = 'no-store'
        return response
