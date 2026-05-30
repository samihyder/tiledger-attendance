"""
WSGI entry point for Vercel deployment.

Environment variables required on Vercel:
  DATABASE_URL        — Supabase connection pooler URL
                        postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
  SECRET_KEY          — Flask session secret (any long random string)
  OVERRIDE_PASSWORD   — Super admin override password
  APP_PREFIX          — URL mount point, set to /attendance
  VERCEL              — Automatically set by Vercel (detects cloud environment)
"""

import os
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix

flask_app = create_app()
flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_prefix=1)

# Mount under APP_PREFIX (e.g. /attendance) when set.
# DispatcherMiddleware sets SCRIPT_NAME so url_for() generates correct prefixed URLs.
prefix = os.environ.get('APP_PREFIX', '').rstrip('/')
if prefix:
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.exceptions import NotFound
    app = DispatcherMiddleware(NotFound(), {prefix: flask_app})
else:
    app = flask_app
