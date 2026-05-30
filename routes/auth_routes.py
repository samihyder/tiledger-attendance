from flask import Blueprint, render_template, request, redirect, url_for, session, flash
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

        user = db.get_user(username)
        if user and db.verify_password(password, user['password_hash']):
            session.permanent = True
            session['user_id']   = user['id']
            session['username']  = user['username']
            session['full_name'] = user['full_name']
            session['role']      = user['role']
            db.update_last_login(user['id'])
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            next_url = request.args.get('next')
            # Store users land directly on the punch screen
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


@auth_bp.route('/verify-override', methods=['POST'])
def verify_override():
    """
    Verify the Super Admin secondary override password.
    Returns JSON — called via AJAX from the manual attendance toggle.
    """
    from flask import jsonify
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
    """Password escalation page for manager/store to access manual attendance."""
    next_url = request.args.get('next') or request.form.get('next_url', '')
    permission = request.args.get('permission', 'manual_attendance')

    if request.method == 'POST':
        password = request.form.get('password', '')
        next_url = request.form.get('next_url', '')
        if password == Config.OVERRIDE_PASSWORD:
            session['override_active'] = True
            return redirect(next_url or url_for('attendance.punch_screen'))
        flash('Incorrect override password.', 'danger')

    permission_labels = {
        'manual_attendance': 'Manual Attendance Entry',
    }
    label = permission_labels.get(permission, permission.replace('_', ' ').title())
    return render_template('request_override.html',
                           next_url=next_url, permission_label=label)
