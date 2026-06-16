from flask import Blueprint, render_template, request, jsonify, session
from auth import login_required, permission_required, current_user
import db_manager as db

overtime_bp = Blueprint('overtime', __name__)


@overtime_bp.route('/')
@login_required
@permission_required('view_payroll')
def queue():
    status_filter = request.args.get('status', 'pending')
    try:
        requests = db.get_overtime_requests(
            status=status_filter if status_filter != 'all' else None
        )
        pending_count = db.get_pending_ot_count()
        db_error = None
    except Exception as e:
        requests = []
        pending_count = 0
        db_error = 'overtime_requests table not found — run migrate_v2.sql in Supabase.'
    return render_template(
        'overtime/queue.html',
        requests=requests,
        status_filter=status_filter,
        pending_count=pending_count,
        db_error=db_error,
        user=current_user(),
    )


@overtime_bp.route('/approve', methods=['POST'])
@login_required
@permission_required('view_payroll')
def approve():
    data = request.get_json(silent=True) or {}
    ot_id = int(data.get('ot_id', 0))
    if not ot_id:
        return jsonify({'success': False, 'error': 'ot_id required'}), 400
    db.approve_overtime(ot_id, session['user_id'])
    return jsonify({'success': True})


@overtime_bp.route('/reject', methods=['POST'])
@login_required
@permission_required('view_payroll')
def reject():
    data = request.get_json(silent=True) or {}
    ot_id  = int(data.get('ot_id', 0))
    reason = data.get('reason', '').strip()
    if not ot_id:
        return jsonify({'success': False, 'error': 'ot_id required'}), 400
    if not reason:
        return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400
    db.reject_overtime(ot_id, session['user_id'], reason)
    return jsonify({'success': True})
