from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from auth import login_required, permission_required, current_user
import db_manager as db
from datetime import date, timedelta
import json

roster_bp = Blueprint('roster', __name__)


@roster_bp.route('/')
@login_required
@permission_required('roster')
def list_rosters():
    today = date.today()
    date_from = request.args.get('date_from', today.strftime('%Y-%m-%d'))
    date_to   = request.args.get('date_to', (today + timedelta(days=6)).strftime('%Y-%m-%d'))
    employee_id = request.args.get('employee_id', type=int)

    rosters   = db.get_rosters(date_from=date_from, date_to=date_to, employee_id=employee_id)
    employees = db.get_employees()

    # Group by date for the list view
    from datetime import datetime as _dt
    grouped: dict = {}
    for r in rosters:
        d = r['roster_date']
        if d not in grouped:
            date_obj = _dt.strptime(d, '%Y-%m-%d').date()
            grouped[d] = {
                'date_str': d,
                'day_name': date_obj.strftime('%A'),
                'display':  date_obj.strftime('%d %b %Y'),
                'entries':  [],
            }
        grouped[d]['entries'].append(r)
    roster_groups = list(grouped.values())

    return render_template(
        'roster/list.html',
        roster_groups=roster_groups,
        total=len(rosters),
        employees=employees,
        date_from=date_from,
        date_to=date_to,
        selected_employee=employee_id,
        user=current_user(),
    )


@roster_bp.route('/shifts')
@login_required
@permission_required('roster')
def list_shifts():
    shifts = db.get_shifts(active_only=False)
    return render_template('roster/shifts.html', shifts=shifts, user=current_user())


@roster_bp.route('/shifts/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_shifts')
def new_shift():
    if request.method == 'POST':
        data = {
            'shift_name':    request.form['shift_name'].strip(),
            'shift_start':   request.form['shift_start'],
            'shift_end':     request.form['shift_end'],
            'grace_minutes': int(request.form.get('grace_minutes', 10)),
        }
        if not data['shift_name']:
            flash('Shift name is required.', 'danger')
        else:
            db.create_shift(data)
            flash(f'Shift "{data["shift_name"]}" created.', 'success')
            return redirect(url_for('roster.list_shifts'))
    return render_template('roster/shift_form.html', shift={}, user=current_user())


@roster_bp.route('/shifts/<int:shift_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_shifts')
def edit_shift(shift_id):
    shift = db.get_shift(shift_id)
    if not shift:
        flash('Shift not found.', 'danger')
        return redirect(url_for('roster.list_shifts'))
    if request.method == 'POST':
        data = {
            'shift_name':    request.form['shift_name'].strip(),
            'shift_start':   request.form['shift_start'],
            'shift_end':     request.form['shift_end'],
            'grace_minutes': int(request.form.get('grace_minutes', 10)),
            'active':        request.form.get('active') == '1',
        }
        db.update_shift(shift_id, data)
        flash('Shift updated.', 'success')
        return redirect(url_for('roster.list_shifts'))
    return render_template('roster/shift_form.html', shift=dict(shift), edit=True, user=current_user())


@roster_bp.route('/assign', methods=['GET', 'POST'])
@login_required
@permission_required('roster')
def assign():
    employees = db.get_employees()
    shifts    = db.get_shifts()

    if request.method == 'POST':
        # JSON batch submit from JS
        payload     = request.get_json()
        employee_id = int(payload.get('employee_id', 0))
        entries     = payload.get('entries', [])   # [{roster_date, shift_id, is_holiday}]
        notes       = payload.get('notes', '').strip()

        if not employee_id:
            return jsonify({'success': False, 'error': 'Employee is required'}), 400
        if not entries:
            return jsonify({'success': False, 'error': 'No roster rows to save'}), 400

        # Validate: non-holiday rows must have a shift
        invalid = [e['roster_date'] for e in entries
                   if not e.get('is_holiday') and not e.get('shift_id')]
        if invalid:
            return jsonify({
                'success': False,
                'error': f'Select a shift for: {", ".join(invalid)}'
            }), 400

        db.save_roster_batch(employee_id, entries, notes, created_by=session['user_id'])
        return jsonify({'success': True, 'saved': len(entries)})

    # Pass weekly_off_day per employee so JS can auto-mark holidays
    emp_off_days = {e['id']: e['weekly_off_day'] for e in employees}
    return render_template(
        'roster/assign.html',
        employees=employees,
        shifts=shifts,
        emp_off_days=emp_off_days,
        user=current_user(),
    )


@roster_bp.route('/<int:roster_id>/delete', methods=['POST'])
@login_required
@permission_required('roster')
def delete_roster(roster_id):
    db.delete_roster(roster_id)
    flash('Roster entry deleted.', 'warning')
    return redirect(url_for('roster.list_rosters'))
