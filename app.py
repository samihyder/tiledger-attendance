"""
TiLedger Attendance — check-in / check-out and face enrolment only.

There is no database here any more (owner 2026-10-08): staff, roster, rules,
punches and faces live in the TiLedger ERP. The app signs in with the ERP
login (opened from TiLedger › Attendance app) and calls the ERP's
/api/attendance-app/* endpoints. See erp_client.py and routes/erp_routes.py.

Run locally: python app.py  →  http://127.0.0.1:5050
"""

import os
from datetime import timedelta
from flask import Flask, jsonify, render_template, request
from flask_compress import Compress
from config import Config
from routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    # The ERP pass decides how long a sign-in lasts (12 h, or 30 days for the
    # punch tablet); the cookie just has to outlive it.
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SECURE'] = bool(os.environ.get('VERCEL'))  # https on Vercel; plain http when run locally
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.url_map.strict_slashes = False

    Compress(app)
    register_blueprints(app)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('erp/message.html', title='Not found', message='This page does not exist.'), 404

    @app.errorhandler(Exception)
    def any_error(e):
        import traceback
        print(traceback.format_exc())
        if '/api/' in (request.path or ''):
            return jsonify({'success': False, 'error': 'Something went wrong — try again'}), 500
        return render_template('erp/message.html', title='Something went wrong', message='Please try again.'), 500

    @app.route('/health')
    def health():
        from erp_client import ERP_BASE_URL
        import urllib.request, urllib.error
        try:  # any HTTP reply (even "not signed in") means TiLedger is reachable
            urllib.request.urlopen(urllib.request.Request(f'{ERP_BASE_URL}/api/attendance-app/today'), timeout=8)
            ok = True
        except urllib.error.HTTPError:
            ok = True
        except Exception:
            ok = False
        return jsonify({'status': 'ok' if ok else 'erp_unreachable', 'erp': ERP_BASE_URL, 'app_root': Config.APPLICATION_ROOT})

    return app


class _PrefixMiddleware:
    """Mount at a subpath (APPLICATION_ROOT, e.g. /attendance) so url_for() keeps the prefix."""
    def __init__(self, wsgi_app, prefix):
        self.app = wsgi_app
        self.prefix = prefix.rstrip('/')

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith(self.prefix):
            environ['PATH_INFO'] = path[len(self.prefix):] or '/'
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + self.prefix
        return self.app(environ, start_response)


app = create_app()

_root = Config.APPLICATION_ROOT
if _root and _root != '/':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = _PrefixMiddleware(app.wsgi_app, _root)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
