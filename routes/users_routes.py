from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from auth import login_required, permission_required, current_user
import db_manager as db

users_bp = Blueprint('users', __name__)

VALID_ROLES = ('super_admin', 'manager', 'system_admin', 'store', 'cashier')


@users_bp.route('/')
@login_required
@permission_required('manage_users')
def list_users():
    users = db.get_app_users()
    return render_template('users/list.html', users=users, user=current_user(),
                           valid_roles=VALID_ROLES)


@users_bp.route('/create', methods=['POST'])
@login_required
@permission_required('manage_users')
def create_user():
    data = request.get_json(silent=True) or {}
    username  = data.get('username', '').strip().lower()
    full_name = data.get('full_name', '').strip()
    role      = data.get('role', '').strip()
    password  = data.get('password', '').strip()

    if not all([username, full_name, role, password]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    if role not in VALID_ROLES:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    try:
        user_id = db.create_app_user(username, password, full_name, role)
        return jsonify({'success': True, 'user_id': user_id})
    except Exception as e:
        msg = str(e)
        if 'unique' in msg.lower() or 'duplicate' in msg.lower():
            msg = f'Username "{username}" is already taken'
        return jsonify({'success': False, 'error': msg}), 500


@users_bp.route('/set-password', methods=['POST'])
@login_required
@permission_required('manage_users')
def set_password():
    data = request.get_json(silent=True) or {}
    user_id  = int(data.get('user_id', 0))
    password = data.get('password', '').strip()
    if not user_id or not password:
        return jsonify({'success': False, 'error': 'user_id and password required'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    if user_id == session.get('user_id') and session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'Cannot change your own password here'}), 403
    db.update_app_user_password(user_id, password)
    return jsonify({'success': True})


@users_bp.route('/toggle', methods=['POST'])
@login_required
@permission_required('manage_users')
def toggle_user():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get('user_id', 0))
    active  = bool(data.get('active', True))
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id required'}), 400
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'error': 'Cannot deactivate yourself'}), 400
    db.toggle_app_user(user_id, active)
    return jsonify({'success': True})
