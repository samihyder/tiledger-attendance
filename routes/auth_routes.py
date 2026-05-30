from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
import db_manager as db
from config import Config
from auth import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        try:
            user = db.get_user(username)
        except Exception as e:
            flash('Database connection failed. Check server configuration.', 'danger')
            return render_template('login.html', db_error=str(e))

        if user and db.verify_password(password, user['password_hash']):
            session.permanent    = True
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['full_name'] = user['full_name']
            session['role']      = user['role']
            try:
                db.update_last_login(user['id'])
            except Exception:
                pass  # non-critical
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            next_url = request.args.get('next')
            if user['role'] == 'store':
                return redirect(next_url or url_for('attendance.punch_screen'))
            return redirect(next_url or url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/health')
def health():
    """Diagnostic endpoint — shows DB connection status and config."""
    status = {
        'vercel':       Config.IS_VERCEL,
        'db_mode':      'postgresql' if db._USE_POSTGRES else 'sqlite',
        'db_url_set':   bool(Config.DATABASE_URL),
        'face_mock':    Config.FACE_MOCK_MODE,
        'biometric_mock': Config.BIOMETRIC_MOCK_MODE,
    }
    try:
        with db.db() as conn:
            conn.execute('SELECT 1')
        status['db_connected'] = True
        status['db_error'] = None
    except Exception as e:
        status['db_connected'] = False
        status['db_error'] = str(e)

    ok = status['db_connected']
    return jsonify(status), 200 if ok else 500


@auth_bp.route('/verify-override', methods=['POST'])
def verify_override():
    password = request.json.get('password', '') if request.is_json else request.form.get('password', '')
    if password == Config.OVERRIDE_PASSWORD:
        session['override_active'] = True
        return ({'valid': True}, 200)
    return ({'valid': False, 'error': 'Incorrect override password'}, 403)


@auth_bp.route('/clear-override', methods=['POST'])
def clear_override():
    session.pop('override_active', None)
    return ({'cleared': True}, 200)


@auth_bp.route('/request-override', methods=['GET', 'POST'])
@login_required
def request_override():
    next_url   = request.args.get('next') or request.form.get('next_url', '')
    permission = request.args.get('permission', 'manual_attendance')

    if request.method == 'POST':
        password = request.form.get('password', '')
        next_url = request.form.get('next_url', '')
        if password == Config.OVERRIDE_PASSWORD:
            session['override_active'] = True
            return redirect(next_url or url_for('attendance.punch_screen'))
        flash('Incorrect override password.', 'danger')

    labels = {'manual_attendance': 'Manual Attendance Entry'}
    label  = labels.get(permission, permission.replace('_', ' ').title())
    return render_template('request_override.html', next_url=next_url, permission_label=label)
