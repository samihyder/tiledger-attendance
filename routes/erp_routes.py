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
    return render_template('erp/punch.html')


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
