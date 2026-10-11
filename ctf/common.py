import secrets
from datetime import timedelta
from flask import abort, request, session

def harden(app):
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      MAX_CONTENT_LENGTH=8192, PERMANENT_SESSION_LIFETIME=timedelta(hours=4))

    @app.before_request
    def csrf_check():
        if request.method == 'POST':
            expected = session.get('csrf', '')
            supplied = request.form.get('csrf', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                abort(400, 'Session expired or invalid form. Reload the page.')

    @app.context_processor
    def csrf_context():
        session.setdefault('csrf', secrets.token_urlsafe(32))
        return dict(csrf=session['csrf'])

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response
