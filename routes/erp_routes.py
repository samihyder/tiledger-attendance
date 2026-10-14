"""
Attendance app routes — check-in / check-out and face enrolment only.
Signed in with the TiLedger ERP login; everything else (staff, roster, rules,
manual attendance, pay) is managed in the ERP's Payroll module.
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from erp_client import call, ErpError, ERP_BASE_URL

erp_bp = Blueprint('erp', __name__)


def _signed_in():
    return bool(session.get('erp_session'))


def need(perm):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not _signed_in():
                if request.path.startswith('/api/') or '/api/' in request.path:
                    return jsonify({'success': False, 'error': 'Signed out — open Attendance from TiLedger again'}), 401
                return redirect(url_for('erp.signin'))
            if perm not in (session.get('erp_perms') or []):
                if '/api/' in request.path:
                    return jsonify({'success': False, 'error': 'Your role cannot do this'}), 403
                return render_template('erp/message.html', title='No access', message='Your TiLedger role does not include this screen.'), 403
            return fn(*a, **kw)
        return wrapper
    return deco


def _proxy(method, path, body=None):
    try:
        return jsonify({'success': True, 'data': call(method, path, session.get('erp_session'), body)})
    except ErpError as e:
        if e.status == 401:
            session.clear()
        return jsonify({'success': False, 'error': str(e)}), e.status


@erp_bp.route('/')
def home():
    if not _signed_in():
        return redirect(url_for('erp.signin'))
    perms = session.get('erp_perms') or []
    return redirect(url_for('erp.punch') if 'attendance:punch' in perms else url_for('erp.enroll'))


@erp_bp.route('/signin')
def signin():
    return render_template('erp/signin.html', erp_url=f'{ERP_BASE_URL}/attendance-app')


@erp_bp.route('/sso')
def sso():
    token = request.args.get('token', '')
    try:
        res = call('POST', '/api/attendance-app/session', body={'token': token})
    except ErpError as e:
        return render_template('erp/message.html', title='Could not sign in', message=str(e), erp_url=f'{ERP_BASE_URL}/attendance-app'), 401
    session.clear()
    session.permanent = True
    session['erp_session'] = res['session']
    session['erp_name'] = res['user']['name']
    session['erp_perms'] = res['user']['perms']
    return redirect(url_for('erp.home'))


@erp_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('erp.signin'))


@erp_bp.route('/punch')
@need('attendance:punch')
def punch():
    return render_template('erp/punch.html', erp_url=f'{ERP_BASE_URL}/attendance-app')


@erp_bp.route('/api/today')
@need('attendance:punch')
def api_today():
    return _proxy('GET', '/api/attendance-app/today')


@erp_bp.route('/api/punch', methods=['POST'])
@need('attendance:punch')
def api_punch():
    return _proxy('POST', '/api/attendance-app/punch', request.get_json(silent=True) or {})


@erp_bp.route('/enroll')
@need('attendance:enroll')
def enroll():
    return render_template('erp/enroll.html')


@erp_bp.route('/api/enroll', methods=['GET', 'POST'])
@need('attendance:enroll')
def api_enroll():
    if request.method == 'GET':
        return _proxy('GET', '/api/attendance-app/enroll')
    return _proxy('POST', '/api/attendance-app/enroll', request.get_json(silent=True) or {})


# ── Installable app (PWA) — iPad / Android tablet "Add to Home Screen" (owner 2026-10-14) ──
@erp_bp.route('/manifest.webmanifest')
def manifest():
    from flask import current_app
    home = url_for('erp.home')
    body = {
        'name': 'TiLedger Attendance', 'short_name': 'Attendance',
        'description': 'Check in and check out with your face — TiLedger by Mutex Systems',
        'id': home, 'start_url': url_for('erp.punch'), 'scope': home,
        'display': 'standalone', 'orientation': 'any',
        'background_color': '#F3F5F9', 'theme_color': '#0F172A',
        'icons': [
            {'src': url_for('static', filename='pwa/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': url_for('static', filename='pwa/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': url_for('static', filename='pwa/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    resp = current_app.response_class(__import__('json').dumps(body), mimetype='application/manifest+json')
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@erp_bp.route('/sw.js')
def service_worker():
    from flask import current_app
    root = url_for('erp.home').rstrip('/') + '/'
    static_root = url_for('static', filename='')
    js = f"""// TiLedger Attendance service worker — makes the punch screen installable and quick to open.
// Static files (styles, face models) are cached; pages are network-first with the last copy as a
// fallback; sign-in and every /api/ call (punches) always go to the network — never cached.
const CACHE = 'tl-attendance-v2'
const STATIC = {static_root!r}
self.addEventListener('install', e => self.skipWaiting())
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())))
self.addEventListener('fetch', e => {{
  const req = e.request, url = new URL(req.url)
  if (req.method !== 'GET' || url.origin !== location.origin) return
  if (url.pathname.includes('/api/') || url.pathname.includes('/sso') || url.pathname.includes('/signin') || url.pathname.includes('/logout')) return
  if (url.pathname.startsWith(STATIC)) {{
    e.respondWith(caches.open(CACHE).then(c => c.match(req).then(hit => hit || fetch(req).then(res => {{ if (res.ok) c.put(req, res.clone()); return res }}))))
    return
  }}
  if (req.mode === 'navigate') {{
    e.respondWith(fetch(req).then(res => {{ if (res.ok && !res.redirected) {{ const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)) }} return res }}).catch(() => caches.match(req)))
  }}
}})
"""
    resp = current_app.response_class(js, mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = root
    resp.headers['Cache-Control'] = 'no-cache'
    return resp
