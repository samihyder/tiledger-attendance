"""
Sync service — mirror attendance data from Supabase DB 1 to ERP Supabase DB 2.

DB 1 (attendance Supabase) is the primary DB — the app writes here directly.
DB 2 (ERP Supabase) is an optional mirror configured via Sync → Settings.

Tables mirrored to DB 2: employees, shifts, rosters, attendance_logs, attendance_daily.

Manager sync windows: 17:00–17:30, 23:30–00:00, 04:00–05:00
Super admin: unrestricted.
"""

import json
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, time as dtime
from config import Config
import db_manager as db


# ── Manager sync windows ──────────────────────────────────────────────────────

MANAGER_SYNC_WINDOWS = [
    (dtime(17,  0), dtime(17, 30)),
    (dtime(23, 30), dtime(23, 59, 59)),
    (dtime(4,   0), dtime(5,  0)),
]


def manager_window_status() -> dict:
    now = datetime.now().time()
    for start, end in MANAGER_SYNC_WINDOWS:
        if start <= now <= end:
            return {'allowed': True, 'window': f'{start.strftime("%H:%M")}–{end.strftime("%H:%M")}'}
    upcoming = [s for s, _ in MANAGER_SYNC_WINDOWS if s > now]
    nxt = min(upcoming) if upcoming else MANAGER_SYNC_WINDOWS[0][0]
    return {'allowed': False, 'window': None, 'next_at': nxt.strftime('%H:%M')}


# ── REST upsert helper ────────────────────────────────────────────────────────

def _sb_upsert(base_url: str, api_key: str, table: str, rows: list) -> None:
    if not rows:
        return
    url  = f'{base_url.rstrip("/")}/rest/v1/{table}'
    body = json.dumps(rows).encode('utf-8')
    req  = urllib.request.Request(
        url, data=body,
        headers={
            'Content-Type':  'application/json',
            'apikey':        api_key,
            'Authorization': f'Bearer {api_key}',
            'Prefer':        'return=minimal,resolution=merge-duplicates',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 201, 204):
            raise RuntimeError(f'{table}: unexpected HTTP {resp.status}')


def _push_to_erp(table: str, rows: list) -> list:
    """Push rows to ERP DB 2. Returns list of error strings."""
    erp = db.get_erp_sync_settings()
    if not erp['url'] or not erp['api_key']:
        return []   # ERP not configured — skip silently
    try:
        _sb_upsert(erp['url'], erp['api_key'], table, rows)
        return []
    except Exception as e:
        return [f'[ERP/{table}] {e}']


# ── Payload builders ──────────────────────────────────────────────────────────

def _employee_rows(employees) -> list:
    return [{
        'id':                        e['id'],
        'employee_code':             e['employee_code'],
        'full_name':                 e['full_name'],
        'department':                e.get('department') or '',
        'designation':               e.get('designation') or '',
        'phone':                     e.get('phone') or '',
        'email':                     e.get('email') or '',
        'joining_date':              e.get('joining_date'),
        'monthly_salary':            float(e.get('monthly_salary') or 0),
        'weekly_off_day':            int(e.get('weekly_off_day') or 6),
        'late_deduction_per_minute': float(e.get('late_deduction_per_minute') or 0),
        'active':                    bool(e.get('active', True)),
    } for e in employees]


def _shift_rows(shifts) -> list:
    return [{
        'id':            s['id'],
        'shift_name':    s['shift_name'],
        'shift_start':   str(s['shift_start']),
        'shift_end':     str(s['shift_end']),
        'grace_minutes': int(s['grace_minutes']),
        'active':        bool(s.get('active', True)),
    } for s in shifts]


def _roster_rows(rosters) -> list:
    return [{
        'id':           r['id'],
        'employee_id':  r['employee_id'],
        'shift_id':     r.get('shift_id'),
        'roster_date':  r['roster_date'],
        'is_holiday':   bool(r.get('is_holiday')),
        'notes':        r.get('notes') or '',
    } for r in rosters]


def _attendance_log_rows(logs) -> list:
    return [{
        'id':             log['id'],
        'employee_id':    log['employee_id'],
        'punch_time':     log['punch_time'],
        'punch_type':     log['punch_type'],
        'punch_source':   log['punch_source'],
        'minutes_late':   int(log.get('minutes_late') or 0),
        'override_reason': log.get('override_reason') or '',
    } for log in logs]


def _build_daily_records(logs: list) -> list:
    daily = defaultdict(lambda: {'in': None, 'out': None})
    for log in logs:
        date = log['punch_time'][:10]
        key  = (log['employee_id'], date)
        if log['punch_type'] == 'in':
            if daily[key]['in'] is None:
                daily[key]['in'] = log
        else:
            daily[key]['out'] = log

    records = []
    for (_emp_id, date), punches in daily.items():
        in_log  = punches['in']
        out_log = punches['out']
        base    = in_log or out_log
        rate      = float(base.get('late_deduction_per_minute') or 0)
        late_mins = int(in_log.get('minutes_late') or 0) if in_log else 0
        records.append({
            'employee_code':    base['employee_code'],
            'full_name':        base['full_name'],
            'department':       base.get('department') or '',
            'designation':      base.get('designation') or '',
            'date':             date,
            'punch_in':         in_log['punch_time'][11:19]  if in_log  else None,
            'punch_out':        out_log['punch_time'][11:19] if out_log else None,
            'minutes_late':     late_mins,
            'deduction_amount': round(late_mins * rate, 2),
            'punch_source':     base.get('punch_source', ''),
            'override_reason':  in_log.get('override_reason') if in_log else None,
        })

    records.sort(key=lambda r: (r['date'], r['employee_code']))
    return records


# ── Public API ────────────────────────────────────────────────────────────────

def sync_reference_data() -> dict:
    """Push employees, shifts, rosters to ERP DB 2."""
    errors = []
    errors += _push_to_erp('employees', _employee_rows(db.get_employees(active_only=False)))
    errors += _push_to_erp('shifts',    _shift_rows(db.get_shifts(active_only=False)))

    from datetime import date, timedelta
    today     = date.today()
    date_from = today.replace(day=1).isoformat()
    date_to   = (today.replace(day=1) + timedelta(days=90)).isoformat()
    rosters   = db.get_rosters(date_from=date_from, date_to=date_to)
    if rosters:
        errors += _push_to_erp('rosters', _roster_rows(rosters))

    return {'success': not errors, 'errors': errors}


def sync_attendance(synced_by: int, role: str = 'super_admin') -> dict:
    """
    Mirror unsynced attendance records to ERP DB 2.
    Marks records as synced only after successful push.
    """
    if role == 'manager':
        ws = manager_window_status()
        if not ws['allowed']:
            return {
                'success': False, 'sent': 0, 'status': 'window_denied',
                'error': f'Sync not available now. Next manager window at {ws.get("next_at","?")}.',
            }

    erp = db.get_erp_sync_settings()
    if not erp['url'] or not erp['api_key']:
        return {
            'success': True, 'sent': 0, 'status': 'no_erp',
            'error': None,
            'message': 'ERP DB not configured — configure it in Sync → Settings.',
        }

    all_errors = []
    all_errors += sync_reference_data()['errors']

    logs = db.get_unsynced_logs()
    if not logs:
        status = 'partial' if all_errors else 'success'
        if all_errors:
            db.record_sync_log(0, status, '; '.join(all_errors), synced_by)
        return {'success': not all_errors, 'sent': 0, 'error': '; '.join(all_errors) or None, 'status': status}

    all_errors += _push_to_erp('attendance_logs', _attendance_log_rows(logs))
    daily      = _build_daily_records(logs)
    all_errors += _push_to_erp('attendance_daily', daily)

    sync_detail = json.dumps([{
        'emp': r['employee_code'], 'name': r['full_name'], 'date': r['date'],
        'in': r['punch_in'], 'out': r['punch_out'], 'deduction': r['deduction_amount'],
    } for r in daily])

    if not all_errors:
        db.mark_synced([l['id'] for l in logs])
        db.record_sync_log(len(daily), 'success', None, synced_by, sync_detail)
        return {'success': True, 'sent': len(daily), 'error': None, 'status': 'success'}

    err_str = '; '.join(all_errors)
    db.record_sync_log(0, 'partial', err_str, synced_by, sync_detail)
    return {'success': False, 'sent': 0, 'error': err_str, 'status': 'partial'}


def full_resync(synced_by: int) -> dict:
    """Force-push ALL attendance logs to ERP DB 2. Use for recovery."""
    erp = db.get_erp_sync_settings()
    if not erp['url'] or not erp['api_key']:
        return {'success': False, 'error': 'ERP DB not configured.'}

    errors  = sync_reference_data()['errors']
    all_logs = db.get_attendance_logs()
    if all_logs:
        errors += _push_to_erp('attendance_logs', _attendance_log_rows(all_logs))
        errors += _push_to_erp('attendance_daily', _build_daily_records(all_logs))

    status = 'success' if not errors else 'partial'
    db.record_sync_log(len(all_logs) if all_logs else 0, status, '; '.join(errors) or None, synced_by)
    return {'success': not errors, 'errors': errors}
