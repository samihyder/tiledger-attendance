"""
Vercel entry point — exposes `app` at module level (required by @vercel/python).

Environment variables (set in Vercel project settings):
  DATABASE_URL         Supabase pooler URL (port 6543, Transaction mode)
  SECRET_KEY           Flask session secret
  OVERRIDE_PASSWORD    Super admin override password
  APP_PREFIX           /attendance
  SESSION_COOKIE_PATH  /attendance
  VERCEL               Set automatically by Vercel runtime
"""

import os
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound

_flask = create_app()
_flask.wsgi_app = ProxyFix(_flask.wsgi_app, x_for=1, x_proto=1, x_prefix=1)

# Mount under APP_PREFIX so url_for() generates /attendance/... URLs.
# Ternary keeps `app` as a single unconditional top-level assignment —
# Vercel requires this to detect the entry point.
_prefix = os.environ.get('APP_PREFIX', '').rstrip('/')

if _prefix:
    from werkzeug.wrappers import Response as _Response

    def _root_redirect(environ, start_response):
        """Redirect bare domain hits to the attendance prefix."""
        res = _Response(status=302, headers={'Location': _prefix + '/'})
        return res(environ, start_response)

    app = DispatcherMiddleware(_root_redirect, {_prefix: _flask})
else:
    app = _flask
