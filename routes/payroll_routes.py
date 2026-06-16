from flask import Blueprint, render_template, request, jsonify, session
from datetime import date
from auth import login_required, permission_required, current_user
import db_manager as db

payroll_bp = Blueprint('payroll', __name__)


def _default_period():
    """Default to current calendar month."""
    today = date.today()
    date_from = today.replace(day=1).strftime('%Y-%m-%d')
    date_to   = today.strftime('%Y-%m-%d')
    return date_from, date_to


@payroll_bp.route('/')
@login_required
@permission_required('view_payroll')
def overview():
    default_from, default_to = _default_period()
    date_from = request.args.get('date_from', default_from)
    date_to   = request.args.get('date_to',   default_to)

    rows = db.get_payroll_overview(date_from, date_to)

    # Grand totals
    totals = {
        'working_days':    sum(r['working_days']    for r in rows),
        'present':         sum(r['present']         for r in rows),
        'absent':          sum(r['absent']           for r in rows),
        'holidays':        sum(r['holidays']         for r in rows),
        'late_days':       sum(r['late_days']        for r in rows),
        'total_late_mins': sum(r['total_late_mins']  for r in rows),
        'total_deduction': round(sum(r['total_deduction'] for r in rows), 2),
    }

    return render_template(
        'payroll/overview.html',
        rows=rows,
        totals=totals,
        date_from=date_from,
        date_to=date_to,
        user=current_user(),
    )


@payroll_bp.route('/<int:employee_id>')
@login_required
@permission_required('view_payroll')
def detail(employee_id):
    default_from, default_to = _default_period()
    date_from = request.args.get('date_from', default_from)
    date_to   = request.args.get('date_to',   default_to)

    try:
        data = db.get_payroll_detail(employee_id, date_from, date_to)
    except Exception as e:
        from flask import flash, redirect, url_for
        flash(f'Payroll data error: {e} — ensure migrate_v2.sql has been run in Supabase.', 'danger')
        return redirect(url_for('payroll.overview'))
    if not data:
        return render_template('404.html', message='Employee not found'), 404

    return render_template(
        'payroll/detail.html',
        data=data,
        date_from=date_from,
        date_to=date_to,
        adj_types=db.ADJ_LABELS,
        user=current_user(),
    )


@payroll_bp.route('/api/adjustments/add', methods=['POST'])
@login_required
@permission_required('view_payroll')
def api_add_adjustment():
    if session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'Super Admin only'}), 403
    data = request.get_json(silent=True) or {}
    try:
        employee_id = int(data.get('employee_id', 0))
        period_from = data.get('period_from', '').strip()
        period_to   = data.get('period_to', '').strip()
        adj_type    = data.get('adj_type', '').strip()
        amount      = float(data.get('amount', 0))
        description = data.get('description', '').strip()
        if not all([employee_id, period_from, period_to, adj_type, description]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be greater than zero'}), 400
        db.add_payroll_adjustment(
            employee_id, period_from, period_to,
            adj_type, amount, description, session['user_id']
        )
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@payroll_bp.route('/api/adjustments/delete', methods=['POST'])
@login_required
@permission_required('view_payroll')
def api_delete_adjustment():
    if session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'Super Admin only'}), 403
    data = request.get_json(silent=True) or {}
    try:
        adj_id      = int(data.get('adj_id', 0))
        employee_id = int(data.get('employee_id', 0))
        if not adj_id or not employee_id:
            return jsonify({'success': False, 'error': 'adj_id and employee_id required'}), 400
        db.delete_payroll_adjustment(adj_id, employee_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
