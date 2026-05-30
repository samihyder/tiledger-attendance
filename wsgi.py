"""
Vercel entry point — `app` must be a single unconditional top-level assignment.

Environment variables (set in Vercel project settings):
  DATABASE_URL         Supabase pooler URL (port 6543, Transaction mode)
  SECRET_KEY           Flask session secret
  OVERRIDE_PASSWORD    Super admin override password
  APP_PREFIX           /attendance
  SESSION_COOKIE_PATH  /attendance
  VERCEL               Set automatically by Vercel runtime
"""

from __future__ import annotations
import os
from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response

_flask = create_app()
_flask.wsgi_app = ProxyFix(_flask.wsgi_app, x_for=1, x_proto=1, x_prefix=1)

_prefix = os.environ.get('APP_PREFIX', '').rstrip('/')


def _root_redirect(environ, start_response):
    """Redirect bare-domain hits to the /attendance prefix."""
    return Response(status=302, headers={'Location': _prefix + '/'})(environ, start_response)


# Single unconditional assignment — Vercel's scanner requires this.
app = DispatcherMiddleware(_root_redirect, {_prefix: _flask}) if _prefix else _flask
