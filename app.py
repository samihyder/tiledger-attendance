"""
TiLedger Attendance System — local Flask server (localhost only).
Run: python app.py
Access: http://127.0.0.1:5050
"""

import os, time

# Apply timezone from TZ_LOCATION env var (TZ is reserved by Vercel)
_tz = os.environ.get('TZ_LOCATION')
if _tz:
    os.environ['TZ'] = _tz
    try:
        time.tzset()
    except AttributeError:
        pass  # Windows — no tzset

from flask import Flask
from config import Config
import db_manager as db
import biometric_service as bio
from routes import register_blueprints

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    # Jinja2 globals
    app.jinja_env.globals['enumerate'] = enumerate

    # Jinja2 filters for payroll templates
    from datetime import date as _date
    _DAY_NAMES = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

    @app.template_filter('datetimeobj')
    def _datetimeobj(s):
        try: return _date.fromisoformat(s)
        except: return None

    @app.template_filter('dayname')
    def _dayname(s):
        try: return _DAY_NAMES[_date.fromisoformat(s).weekday()]
        except: return ''

    @app.template_filter('dayofweek')
    def _dayofweek(s):
        try: return _date.fromisoformat(s).weekday()   # 0=Mon … 6=Sun
        except: return -1

    # Initialise DB (creates tables + seeds defaults if fresh install)
    db.init_db()

    # Open biometric device at startup
    try:
        bio.open_device()
        print('[OK] Biometric device ready')
    except Exception as e:
        print(f'[WARN] Biometric device not available: {e}')
        print('[WARN] Set BIOMETRIC_MOCK=true to run without hardware')

    register_blueprints(app)

    # Shutdown device cleanly on app teardown
    import atexit
    atexit.register(bio.close_device)

    return app


class _PrefixMiddleware:
    """
    Sets SCRIPT_NAME so Flask's url_for() generates correct URLs when the app
    is mounted at a subpath (e.g. kitchenos.chipyeat.com/attendance).
    Without this, redirects and url_for() would produce paths without the prefix.
    """
    def __init__(self, wsgi_app, prefix):
        self.app = wsgi_app
        self.prefix = prefix.rstrip('/')

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith(self.prefix):
            environ['PATH_INFO'] = path[len(self.prefix):] or '/'
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + self.prefix
        return self.app(environ, start_response)


# Expose app at module level for Vercel / WSGI
app = create_app()

# Mount at subpath when APPLICATION_ROOT is set (e.g. /attendance on Vercel)
_root = Config.APPLICATION_ROOT
if _root and _root != '/':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = _PrefixMiddleware(app.wsgi_app, _root)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == '__main__':
    print(f'\n  TiLedger Attendance System')
    print(f'  URL  : http://{Config.HOST}:{Config.PORT}')
    print(f'  Login: admin / admin@2026  (change immediately)\n')
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
