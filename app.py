"""
TiLedger Attendance System — local Flask server (localhost only).
Run: python app.py
Access: http://127.0.0.1:5050
"""

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

    # Initialise DB lazily on first request — NOT at import time.
    # Calling it at startup crashes Vercel serverless functions because the
    # PostgreSQL connection attempt happens before the function is ready.
    _db_ready = False

    @app.before_request
    def _lazy_init_db():
        nonlocal _db_ready
        if not _db_ready:
            try:
                db.init_db()
            except Exception as e:
                app.logger.warning(f'DB init skipped: {e}')
            _db_ready = True

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


if __name__ == '__main__':
    app = create_app()
    print(f'\n  TiLedger Attendance System')
    print(f'  URL  : http://{Config.HOST}:{Config.PORT}')
    print(f'  Login: admin / admin@2026  (change immediately)\n')
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
