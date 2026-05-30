from __future__ import annotations

"""
Core attendance business logic — late calculation, punch processing, roster enforcement.
"""

from datetime import datetime, timedelta, date
import db_manager as db
from config import Config


def calculate_minutes_late(punch_time: datetime, shift_start_str: str, grace_minutes: int) -> int:
    """
    Compare punch_time against shift_start + grace_period.
    Returns minutes late measured from shift_start (0 if within grace window).
    """
    shift_h, shift_m = map(int, shift_start_str.split(':'))
    shift_start = punch_time.replace(hour=shift_h, minute=shift_m, second=0, microsecond=0)
    grace_end = shift_start + timedelta(minutes=grace_minutes)
    if punch_time <= grace_end:
        return 0
    return max(0, int((punch_time - shift_start).total_seconds() / 60))


def determine_punch_type(employee_id: int, punch_date_str: str) -> str:
    last = db.get_last_punch(employee_id, punch_date_str)
    if last is None or last['punch_type'] == 'out':
        return 'in'
    return 'out'


def check_roster_for_punch(employee_id: int, date_str: str) -> tuple[dict | None, str | None]:
    """
    Returns (roster, error_message).
    roster is None and error_message is set if punching is blocked.
    """
    roster = db.get_roster_for_date(employee_id, date_str)
    if not roster:
        employee = db.get_employee(employee_id)
        name = employee['full_name'] if employee else 'Employee'
        return None, f'No roster assigned for {name} on {date_str}. Contact your manager.'
    if roster['is_holiday']:
        return roster, f'Today is a scheduled holiday — no punch required.'
    return roster, None


def process_biometric_punch(employee_id: int) -> dict:
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    punch_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    employee = db.get_employee(employee_id)
    if not employee:
        return {'success': False, 'error': 'Employee not found'}

    # Cooldown
    last = db.get_last_punch(employee_id, today)
    if last:
        last_time = datetime.strptime(last['punch_time'], '%Y-%m-%d %H:%M:%S')
        elapsed = (now - last_time).total_seconds() / 60
        if elapsed < Config.PUNCH_COOLDOWN_MINUTES:
            return {'success': False, 'error': f'Already punched {int(elapsed * 60)}s ago — please wait'}

    # Roster enforcement
    roster, roster_error = check_roster_for_punch(employee_id, today)
    if roster_error and not roster:
        return {'success': False, 'error': roster_error}

    punch_type = determine_punch_type(employee_id, today)
    minutes_late = 0
    roster_id = roster['id'] if roster else None

    if roster and not roster['is_holiday'] and punch_type == 'in':
        minutes_late = calculate_minutes_late(now, roster['shift_start'], roster['grace_minutes'])

    log_id = db.record_punch(
        employee_id=employee_id,
        punch_time=punch_time_str,
        punch_type=punch_type,
        punch_source='biometric',
        minutes_late=minutes_late,
        roster_id=roster_id,
    )

    return {
        'success': True,
        'log_id': log_id,
        'employee_id': employee_id,
        'employee_name': employee['full_name'],
        'employee_code': employee['employee_code'],
        'punch_type': punch_type,
        'punch_time': punch_time_str,
        'minutes_late': minutes_late,
        'on_time': minutes_late == 0,
    }


def process_manual_day_punch(employee_id: int, override_by: int) -> dict:
    """Manual punch from the punch screen (manual mode active for today)."""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    punch_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    employee = db.get_employee(employee_id)
    if not employee:
        return {'success': False, 'error': 'Employee not found'}

    # Cooldown
    last = db.get_last_punch(employee_id, today)
    if last:
        last_time = datetime.strptime(last['punch_time'], '%Y-%m-%d %H:%M:%S')
        elapsed = (now - last_time).total_seconds() / 60
        if elapsed < Config.PUNCH_COOLDOWN_MINUTES:
            return {'success': False, 'error': f'{employee["full_name"]} already punched {int(elapsed * 60)}s ago'}

    # Roster enforcement
    roster, roster_error = check_roster_for_punch(employee_id, today)
    if roster_error and not roster:
        return {'success': False, 'error': roster_error}

    punch_type = determine_punch_type(employee_id, today)
    minutes_late = 0
    roster_id = roster['id'] if roster else None

    if roster and not roster['is_holiday'] and punch_type == 'in':
        minutes_late = calculate_minutes_late(now, roster['shift_start'], roster['grace_minutes'])

    log_id = db.record_punch(
        employee_id=employee_id,
        punch_time=punch_time_str,
        punch_type=punch_type,
        punch_source='manual',
        minutes_late=minutes_late,
        roster_id=roster_id,
        override_reason='Manual mode active for day',
        override_by=override_by,
    )

    return {
        'success': True,
        'log_id': log_id,
        'employee_id': employee_id,
        'employee_name': employee['full_name'],
        'employee_code': employee['employee_code'],
        'punch_type': punch_type,
        'punch_time': punch_time_str,
        'minutes_late': minutes_late,
        'on_time': minutes_late == 0,
    }


def process_manual_punch(employee_id: int, punch_type: str, punch_time_str: str,
                         override_reason: str, override_by: int) -> dict:
    """Backdated correction — super admin only, no roster enforcement."""
    try:
        punch_time = datetime.strptime(punch_time_str, '%Y-%m-%d %H:%M')
    except ValueError:
        punch_time = datetime.strptime(punch_time_str, '%Y-%m-%d %H:%M:%S')

    today = punch_time.strftime('%Y-%m-%d')
    employee = db.get_employee(employee_id)
    if not employee:
        return {'success': False, 'error': 'Employee not found'}

    roster = db.get_roster_for_date(employee_id, today)
    minutes_late = 0
    roster_id = None

    if roster and not roster['is_holiday'] and punch_type == 'in':
        minutes_late = calculate_minutes_late(punch_time, roster['shift_start'], roster['grace_minutes'])
        roster_id = roster['id']

    log_id = db.record_punch(
        employee_id=employee_id,
        punch_time=punch_time.strftime('%Y-%m-%d %H:%M:%S'),
        punch_type=punch_type,
        punch_source='manual',
        minutes_late=minutes_late,
        roster_id=roster_id,
        override_reason=override_reason,
        override_by=override_by,
    )

    return {
        'success': True,
        'log_id': log_id,
        'employee_name': employee['full_name'],
        'punch_type': punch_type,
        'minutes_late': minutes_late,
    }


def get_daily_summary(date_str: str) -> list[dict]:
    """Per-employee summary: first-in, last-out, hours worked, late mins, deduction amount."""
    logs = db.get_attendance_logs(date_from=date_str, date_to=date_str)
    employees_map = {e['id']: dict(e) for e in db.get_employees(active_only=False)}

    by_employee: dict[int, dict] = {}
    for log in logs:
        eid = log['employee_id']
        emp = employees_map.get(eid, {})
        if eid not in by_employee:
            by_employee[eid] = {
                'employee_id': eid,
                'employee_code': log['employee_code'],
                'full_name': log['full_name'],
                'first_in': None,
                'last_out': None,
                'minutes_late': 0,
                'late_deduction_per_minute': float(emp.get('late_deduction_per_minute', 0) or 0),
                'punches': 0,
            }
        entry = by_employee[eid]
        entry['punches'] += 1

        if log['punch_type'] == 'in':
            t = log['punch_time']
            if entry['first_in'] is None or t < entry['first_in']:
                entry['first_in'] = t
                entry['minutes_late'] = log['minutes_late']
        else:
            t = log['punch_time']
            if entry['last_out'] is None or t > entry['last_out']:
                entry['last_out'] = t

    for entry in by_employee.values():
        if entry['first_in'] and entry['last_out']:
            t_in  = datetime.strptime(entry['first_in'],  '%Y-%m-%d %H:%M:%S')
            t_out = datetime.strptime(entry['last_out'],  '%Y-%m-%d %H:%M:%S')
            entry['hours_worked'] = round((t_out - t_in).total_seconds() / 3600, 2)
        else:
            entry['hours_worked'] = None

        rate = entry['late_deduction_per_minute']
        entry['late_deduction_amount'] = round(entry['minutes_late'] * rate, 2) if rate else 0

    return sorted(by_employee.values(), key=lambda x: x['full_name'])
