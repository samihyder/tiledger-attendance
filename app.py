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
    app.url_map.strict_slashes = False  # accept /employees and /employees/ without redirect

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

    # ── Shift-end auto-logout (04:00 AM) ─────────────────────────────────────
    @app.before_request
    def auto_logout_at_shift_end():
        from flask import session as s, request as req, redirect as redir, url_for as uf, flash as fl
        if 'user_id' not in s:
            return
        if req.endpoint in ('auth.login', 'auth.logout', 'auth.verify_override',
                             'auth.clear_override', 'health', None):
            return
        login_time_str = s.get('login_time')
        if not login_time_str:
            return
        from datetime import datetime as dt
        now = dt.now()
        today_cutoff = now.replace(hour=4, minute=0, second=0, microsecond=0)
        try:
            login_time = dt.fromisoformat(login_time_str)
        except Exception:
            return
        if now >= today_cutoff and login_time < today_cutoff:
            s.clear()
            fl('Shift ended — you have been automatically logged out at 04:00 AM.', 'info')
            return redir(uf('auth.login'))

    # ── Template context: logout lock flag ───────────────────────────────────
    @app.context_processor
    def inject_logout_context():
        from flask import session as s
        from datetime import datetime as dt
        h = dt.now().hour
        in_shift = h >= 19 or h < 4
        role = s.get('role', '')
        return {'logout_locked': in_shift and role in ('store', 'manager')}

    # Return JSON (not HTML) for any unhandled exception on API endpoints
    @app.errorhandler(Exception)
    def api_error(e):
        import traceback
        from flask import request as req, jsonify as jfy
        print(traceback.format_exc())
        if req.path and '/api/' in req.path:
            return jfy({'success': False, 'error': str(e)}), 500
        raise e

    # Diagnostic endpoint — no auth
    @app.route('/health')
    def health():
        import os, urllib.error
        from flask import jsonify
        db_error = None
        try:
            db._get('app_users', 'id', limit=1)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            db_error = f'HTTP {e.code}: {body}'
        except Exception as e:
            db_error = str(e)
        supabase_keys = [k for k in os.environ if 'SUPA' in k.upper()]
        url = Config.SUPABASE_URL
        return jsonify({
            'status':            'ok' if db_error is None else 'db_error',
            'supabase_url':      (url[:50] + '...') if len(url) > 50 else url,
            'service_key_set':   bool(Config.SUPABASE_SERVICE_KEY),
            'app_root':          Config.APPLICATION_ROOT,
            'db_error':          db_error,
            'env_keys_with_supa': supabase_keys,
        })

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
