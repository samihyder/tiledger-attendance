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
    shift_h, shift_m = map(int, shift_start_str.split(':')[:2])
    shift_start = punch_time.replace(hour=shift_h, minute=shift_m, second=0, microsecond=0)
    grace_end = shift_start + timedelta(minutes=grace_minutes)
    if punch_time <= grace_end:
        return 0
    return max(0, int((punch_time - shift_start).total_seconds() / 60))


def determine_punch_type(employee_id: int, punch_date_str: str) -> str | None:
    """
    Returns 'in', 'out', or None.
    None means a complete IN→OUT cycle already exists for this shift — block further punches.
    Uses the shift window (19:00-04:00 for night shifts) so cross-midnight punches are seen.
    """
    shift_punches = db.get_shift_punches(employee_id, punch_date_str)
    ins  = [p for p in shift_punches if p['punch_type'] == 'in']
    outs = [p for p in shift_punches if p['punch_type'] == 'out']
    if not ins:
        return 'in'
    if not outs:
        return 'out'
    return None  # shift complete


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


def _get_roster_for_punch(employee_id: int, today: str, punch_type: str):
    """
    Look up the roster for punch validation.
    For OUT punches that cross midnight (night shift), also checks yesterday.
    Returns (roster_or_None, block_error_or_None).
    Roster blocking is only applied for punch-IN.
    """
    from datetime import timedelta as _td
    roster = db.get_roster_for_date(employee_id, today)

    # Night-shift OUT: if punching out before 04:00 and no roster today, try yesterday
    now_h = datetime.now().hour
    if not roster and punch_type == 'out' and now_h < 4:
        prev = (datetime.strptime(today, '%Y-%m-%d') - _td(days=1)).strftime('%Y-%m-%d')
        roster = db.get_roster_for_date(employee_id, prev)

    if not roster:
        if punch_type == 'in':
            emp = db.get_employee(employee_id)
            name = emp['full_name'] if emp else 'Employee'
            return None, f'{name} is not scheduled to work today — contact your manager.'
        return None, None   # OUT with no roster: allow (shift already started)

    if roster['is_holiday'] and punch_type == 'in':
        return roster, 'Today is a scheduled day off — no punch required.'

    return roster, None


def process_biometric_punch(employee_id: int) -> dict:
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    punch_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    employee = db.get_employee(employee_id)
    if not employee:
        return {'success': False, 'error': 'Employee not found'}

    # Deactivated check
    if not employee.get('active', True):
        return {'success': False, 'error': f'{employee["full_name"]} is deactivated — contact your manager'}

    # Cooldown
    last = db.get_last_punch(employee_id, today)
    if last:
        last_time = datetime.strptime(last['punch_time'], '%Y-%m-%d %H:%M:%S')
        elapsed = (now - last_time).total_seconds() / 60
        if elapsed < Config.PUNCH_COOLDOWN_MINUTES:
            return {'success': False, 'error': f'Already punched {int(elapsed * 60)}s ago — please wait'}

    # Check shift status first
    punch_type = determine_punch_type(employee_id, today)
    if punch_type is None:
        return {'success': False, 'error': f'{employee["full_name"]} has already completed their shift today (punched in and out)'}
    if punch_type == 'in':
        last = db.get_last_punch(employee_id, today)
        if last and last['punch_type'] == 'in':
            return {'success': False, 'error': f'{employee["full_name"]} is already punched in — please punch out first'}

    # Roster enforcement (blocks punch-IN only; OUT allowed across midnight for night shift)
    roster, roster_error = _get_roster_for_punch(employee_id, today, punch_type)
    if roster_error:
        return {'success': False, 'error': roster_error}

    minutes_late = 0
    roster_id = roster['id'] if roster else None

    if roster and not roster.get('is_holiday') and punch_type == 'in':
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
        'shift_start': roster['shift_start'][:5] if roster and not roster['is_holiday'] else None,
    }


def process_manual_day_punch(employee_id: int, override_by: int) -> dict:
    """Manual punch from the punch screen (manual mode active for today)."""
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    punch_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    employee = db.get_employee(employee_id)
    if not employee:
        return {'success': False, 'error': 'Employee not found'}

    # Deactivated check
    if not employee.get('active', True):
        return {'success': False, 'error': f'{employee["full_name"]} is deactivated — contact your manager'}

    # Check shift status
    punch_type = determine_punch_type(employee_id, today)
    if punch_type is None:
        return {'success': False, 'error': f'{employee["full_name"]} has already completed their shift today'}
    if punch_type == 'in':
        last = db.get_last_punch(employee_id, today)
        if last and last['punch_type'] == 'in':
            return {'success': False, 'error': f'{employee["full_name"]} is already punched in'}

    # Cooldown
    last = db.get_last_punch(employee_id, today)
    if last:
        last_time = datetime.strptime(last['punch_time'], '%Y-%m-%d %H:%M:%S')
        elapsed = (now - last_time).total_seconds() / 60
        if elapsed < Config.PUNCH_COOLDOWN_MINUTES:
            return {'success': False, 'error': f'{employee["full_name"]} already punched {int(elapsed * 60)}s ago — wait a moment'}

    # Roster enforcement (blocks punch-IN only)
    roster, roster_error = _get_roster_for_punch(employee_id, today, punch_type)
    if roster_error:
        return {'success': False, 'error': roster_error}

    minutes_late = 0
    roster_id = roster['id'] if roster else None

    if roster and not roster.get('is_holiday') and punch_type == 'in':
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
        'shift_start': roster['shift_start'][:5] if roster and not roster['is_holiday'] else None,
    }


def process_manual_punch(employee_id: int, punch_type: str, punch_time_str: str,
                         override_reason: str, override_by: int) -> dict:
    """Backdated correction — super admin only, no roster enforcement."""
    punch_time_str = punch_time_str.replace('T', ' ')  # normalize datetime-local input
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
    """Per-employee summary: first-in, last-out, hours worked, late mins, deduction amount.

    For night shifts that cross midnight, OUT punches on the next day before 04:00 AM
    are included so hours_worked is calculated correctly.
    """
    from datetime import timedelta
    next_day = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    logs = db.get_attendance_logs(date_from=date_str, date_to=date_str)
    # Grab next-day early-morning punches (night shift overlap) — OUT only
    next_morn = [
        l for l in db.get_attendance_logs(date_from=next_day, date_to=next_day)
        if l['punch_time'][11:13] < '04' and l['punch_type'] == 'out'
    ]
    # Only add these OUT punches for employees who already have an IN on date_str
    date_str_employees = {l['employee_id'] for l in logs if l['punch_type'] == 'in'}
    logs = logs + [l for l in next_morn if l['employee_id'] in date_str_employees]
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


# ── Shift date helper ─────────────────────────────────────────────────────────

def _shift_date(punch_time_str: str) -> str:
    """
    Return the 'shift date' for a punch: punches before 04:00 AM belong to
    the previous calendar day's night shift.
    """
    if punch_time_str[11:13] < '04':
        prev = datetime.strptime(punch_time_str[:10], '%Y-%m-%d') - timedelta(days=1)
        return prev.strftime('%Y-%m-%d')
    return punch_time_str[:10]


# ── Deduplication ─────────────────────────────────────────────────────────────

def build_dedup_plan(date_from: str, date_to: str) -> dict:
    """
    Analyse punches in [date_from, date_to] and return a plan showing which
    records to keep and which to delete.

    Rules:
      - Group by (employee_id, shift_date)  where shift_date uses _shift_date()
      - Per group: keep the EARLIEST IN and LATEST OUT; flag the rest for deletion
      - Also recalculate minutes_late for the kept IN against the roster shift_start

    Returns:
      {
        'to_delete': [id, ...],
        'to_update': [(id, minutes_late), ...],  # kept INs whose late mins may change
        'groups':    [...summary dicts for display...]
      }
    """
    from collections import defaultdict
    rows = db.get_all_punches_for_dedup(date_from, date_to)

    # Group by (employee_id, shift_date)
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        key = (r['employee_id'], _shift_date(r['punch_time']))
        groups[key].append(r)

    to_delete: list[int] = []
    to_update: list[tuple] = []
    summary: list[dict] = []

    for (emp_id, shift_date), punches in groups.items():
        ins  = sorted([p for p in punches if p['punch_type'] == 'in'],  key=lambda p: p['punch_time'])
        outs = sorted([p for p in punches if p['punch_type'] == 'out'], key=lambda p: p['punch_time'])

        keep_in  = ins[0]  if ins  else None
        keep_out = outs[-1] if outs else None

        # IDs to delete: all but the kept ones
        del_ids = [p['id'] for p in ins[1:]] + [p['id'] for p in outs[:-1]]
        to_delete.extend(del_ids)

        # Recalculate minutes_late for kept IN
        if keep_in:
            roster = db.get_roster_for_date(emp_id, shift_date)
            if roster and not roster['is_holiday']:
                punch_dt = datetime.strptime(keep_in['punch_time'], '%Y-%m-%d %H:%M:%S')
                new_late = calculate_minutes_late(punch_dt, roster['shift_start'], roster['grace_minutes'])
                if new_late != (keep_in.get('minutes_late') or 0):
                    to_update.append((keep_in['id'], new_late))

        summary.append({
            'employee_id': emp_id,
            'shift_date':  shift_date,
            'kept_in':     keep_in['punch_time'] if keep_in else None,
            'kept_out':    keep_out['punch_time'] if keep_out else None,
            'deleted':     del_ids,
            'total':       len(punches),
        })

    return {
        'to_delete': to_delete,
        'to_update': to_update,
        'groups':    sorted(summary, key=lambda x: (x['shift_date'], x['employee_id'])),
    }


def run_deduplication(date_from: str, date_to: str) -> dict:
    """Execute the dedup plan and return counts."""
    plan = build_dedup_plan(date_from, date_to)
    deleted = db.delete_punches_by_ids(plan['to_delete'])
    for punch_id, new_late in plan['to_update']:
        db.update_punch_minutes_late(punch_id, new_late)
    return {
        'deleted': deleted,
        'updated': len(plan['to_update']),
        'groups':  len(plan['groups']),
    }
