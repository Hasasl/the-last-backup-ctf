import json
from pathlib import Path
from flask import Flask, abort, jsonify, render_template, request, send_file, session
from .common import harden
from .attempt_guard import reserve

def create_app(config):
    app = Flask(__name__)
    app.config.update(config)
    harden(app)
    root = Path(app.config['DATA_DIR'])
    fixtures = json.loads((root / 'fixtures.json').read_text())
    private = json.loads((root / 'private.json').read_text())

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.get('/')
    def index():
        return render_template('portal.html', title='Evidence review', fixtures=fixtures,
                               reviewed=session.get('reviewed', False), flag=private['flag'] if session.get('reviewed') else None)

    @app.get('/api/audit')
    def audit():
        ref = request.args.get('reference')
        return jsonify([row for row in fixtures['audit'] if not ref or row['reference'] == ref])

    @app.post('/review')
    def review():
        retry = reserve(app.config.get('GUARD_DATABASE', root / 'portal-guard.sqlite'), request.remote_addr or 'local')
        if retry:
            return render_template('portal.html', title='Evidence review', fixtures=fixtures,
                reviewed=session.get('reviewed', False), flag=None,
                message=f'Too many attempts. Try again in {retry} seconds.'), 429, {'Retry-After': str(retry)}
        pair = [request.form.get('transaction', ''), request.form.get('audit', '')]
        valid = pair == private['evidence_pair']
        if valid:
            session['reviewed'] = True
        return render_template('portal.html', title='Evidence review', fixtures=fixtures,
                               reviewed=session.get('reviewed', False),
                               flag=private['flag'] if session.get('reviewed') else None,
                               message='Evidence corroborated. Elias’s files are released.' if valid else 'That pair does not establish the authorization mismatch.'), (200 if valid else 400)

    @app.get('/attachments/<name>')
    def attachment(name):
        if not session.get('reviewed'):
            abort(403)
        if name not in ('elias.enc.txt', 'training-memo.txt'):
            abort(404)
        return send_file(root / name, as_attachment=True)

    return app
