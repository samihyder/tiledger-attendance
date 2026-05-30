from flask import Blueprint, render_template, request
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

    data = db.get_payroll_detail(employee_id, date_from, date_to)
    if not data:
        return 'Employee not found', 404

    return render_template(
        'payroll/detail.html',
        data=data,
        date_from=date_from,
        date_to=date_to,
        user=current_user(),
    )
