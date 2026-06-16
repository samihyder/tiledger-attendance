from flask import Blueprint, render_template, request, jsonify, session
from auth import login_required, permission_required, current_user
import db_manager as db
from datetime import datetime

leave_bp = Blueprint('leave', __name__)


@leave_bp.route('/')
@login_required
@permission_required('view_attendance')
def list_leave():
    status_filter = request.args.get('status', 'pending')
    try:
        requests = db.get_leave_requests(
            status=status_filter if status_filter != 'all' else None
        )
        pending_count = db.get_pending_leave_count()
        db_error = None
    except Exception as e:
        requests = []
        pending_count = 0
        db_error = 'leave_requests table not found — run migrate_v2.sql in Supabase.'
    employees = db.get_employees(active_only=True)
    return render_template(
        'leave/list.html',
        requests=requests,
        status_filter=status_filter,
        pending_count=pending_count,
        employees=employees,
        leave_types=db.LEAVE_LABELS,
        db_error=db_error,
        user=current_user(),
    )


@leave_bp.route('/create', methods=['POST'])
@login_required
@permission_required('view_attendance')
def create_leave():
    data = request.get_json(silent=True) or {}
    employee_id = int(data.get('employee_id', 0))
    leave_type  = data.get('leave_type', '').strip()
    date_from   = data.get('date_from', '').strip()
    date_to     = data.get('date_to', '').strip()
    reason      = data.get('reason', '').strip()

    if not all([employee_id, leave_type, date_from, date_to]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    if leave_type not in db.LEAVE_TYPES:
        return jsonify({'success': False, 'error': 'Invalid leave type'}), 400
    try:
        d_from = datetime.strptime(date_from, '%Y-%m-%d')
        d_to   = datetime.strptime(date_to,   '%Y-%m-%d')
        days   = max(1, (d_to - d_from).days + 1)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    try:
        db.create_leave_request(employee_id, leave_type, date_from, date_to, days, reason)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@leave_bp.route('/approve', methods=['POST'])
@login_required
@permission_required('view_attendance')
def approve():
    if session.get('role') not in ('super_admin', 'manager'):
        return jsonify({'success': False, 'error': 'Manager or above required'}), 403
    data = request.get_json(silent=True) or {}
    leave_id = int(data.get('leave_id', 0))
    if not leave_id:
        return jsonify({'success': False, 'error': 'leave_id required'}), 400
    db.approve_leave(leave_id, session['user_id'])
    return jsonify({'success': True})


@leave_bp.route('/reject', methods=['POST'])
@login_required
@permission_required('view_attendance')
def reject():
    if session.get('role') not in ('super_admin', 'manager'):
        return jsonify({'success': False, 'error': 'Manager or above required'}), 403
    data = request.get_json(silent=True) or {}
    leave_id = int(data.get('leave_id', 0))
    reason   = data.get('reason', '').strip()
    if not leave_id:
        return jsonify({'success': False, 'error': 'leave_id required'}), 400
    if not reason:
        return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400
    db.reject_leave(leave_id, session['user_id'], reason)
    return jsonify({'success': True})
