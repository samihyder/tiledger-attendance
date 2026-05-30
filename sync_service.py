"""
Sync service — push daily attendance records (punch in/out + deduction) to ERP.

Payload sent per daily record:
  employee_code, full_name, department, designation, date,
  punch_in, punch_out, minutes_late, deduction_amount,
  punch_source, override_reason
"""

import json
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, time as dtime
from config import Config
import db_manager as db


# ──────────────────────────────────────────────────────────────────────────────
# Manager sync windows: (start, end) — inclusive
# Super admin can always sync.
# ──────────────────────────────────────────────────────────────────────────────
MANAGER_SYNC_WINDOWS = [
    (dtime(17,  0), dtime(17, 30)),      # 17:00 – 17:30
    (dtime(23, 30), dtime(23, 59, 59)),  # 23:30 – midnight
    (dtime(4,   0), dtime(5,  0)),       # 04:00 – 05:00
]


def manager_window_status() -> dict:
    """
    Returns current window state for manager role.
      allowed  : bool — can sync right now
      next_window : str — human-readable label of next/current window
    """
    now = datetime.now().time()
    for start, end in MANAGER_SYNC_WINDOWS:
        if start <= now <= end:
            return {'allowed': True, 'window': f'{start.strftime("%H:%M")}–{end.strftime("%H:%M")}'}

    # Find next upcoming window (today or tomorrow)
    upcoming = []
    for start, _ in MANAGER_SYNC_WINDOWS:
        if start > now:
            upcoming.append(start)
    if upcoming:
        nxt = min(upcoming)
    else:
        nxt = MANAGER_SYNC_WINDOWS[0][0]  # wraps to first window tomorrow

    return {'allowed': False, 'window': None, 'next_at': nxt.strftime('%H:%M')}


def _build_daily_records(logs: list) -> list[dict]:
    """
    Group individual punch records by (employee_id, date) and build daily records.
    Keeps first punch-in and last punch-out of each day.
    """
    daily: dict = defaultdict(lambda: {'in': None, 'out': None})

    for log in logs:
        date = log['punch_time'][:10]
        key = (log['employee_id'], date)
        if log['punch_type'] == 'in':
            if daily[key]['in'] is None:
                daily[key]['in'] = log          # first punch-in
        else:
            daily[key]['out'] = log             # always overwrite → last punch-out

    records = []
    for (_emp_id, date), punches in daily.items():
        in_log  = punches['in']
        out_log = punches['out']
        base    = in_log or out_log

        rate      = base.get('late_deduction_per_minute') or 0
        late_mins = (in_log.get('minutes_late') or 0) if in_log else 0
        deduction = round(late_mins * rate, 2)

        records.append({
            'employee_code':   base['employee_code'],
            'full_name':       base['full_name'],
            'department':      base.get('department') or '',
            'designation':     base.get('designation') or '',
            'date':            date,
            'punch_in':        in_log['punch_time'][11:19]  if in_log  else None,
            'punch_out':       out_log['punch_time'][11:19] if out_log else None,
            'minutes_late':    late_mins,
            'deduction_amount': deduction,
            'punch_source':    (in_log or out_log).get('punch_source', ''),
            'override_reason': in_log.get('override_reason') if in_log else None,
        })

    records.sort(key=lambda r: (r['date'], r['employee_code']))
    return records


def _build_sync_detail(records: list[dict]) -> str:
    """Compact JSON summary stored in sync_log.sync_detail for the history view."""
    summary = [
        {
            'emp':       r['employee_code'],
            'name':      r['full_name'],
            'date':      r['date'],
            'in':        r['punch_in'],
            'out':       r['punch_out'],
            'deduction': r['deduction_amount'],
        }
        for r in records
    ]
    return json.dumps(summary)


def sync_attendance(synced_by: int, role: str = 'super_admin') -> dict:
    """
    Build daily attendance payload, POST to ERP, mark records synced.

    Args:
        synced_by: app_users.id of the user triggering sync
        role:      caller's role — manager is time-window restricted

    Returns:
        {'success': bool, 'sent': int, 'error': str|None, 'status': str}
    """
    # Time-window enforcement for manager
    if role == 'manager':
        ws = manager_window_status()
        if not ws['allowed']:
            next_at = ws.get('next_at', '?')
            return {
                'success': False,
                'sent': 0,
                'error': f'Sync not available now. Manager windows: 17:00, 23:30, 04:00–05:00. Next window at {next_at}.',
                'status': 'window_denied',
            }

    cfg = db.get_sync_settings()
    if not cfg['url'] or not cfg['api_key']:
        return {
            'success': False,
            'sent': 0,
            'error': 'Supabase URL or API key not configured. Go to Sync → Settings.',
            'status': 'failed',
        }

    logs = db.get_unsynced_logs()
    if not logs:
        return {'success': True, 'sent': 0, 'error': None, 'status': 'success'}

    daily_records = _build_daily_records(logs)
    sync_detail   = _build_sync_detail(daily_records)

    # Supabase PostgREST upsert:
    #   POST /rest/v1/<table>
    #   Prefer: resolution=merge-duplicates  → upsert on unique (employee_code, date)
    url  = f'{cfg["url"].rstrip("/")}/rest/v1/{cfg["table"]}'
    body = json.dumps(daily_records).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type':  'application/json',
            'apikey':        cfg['api_key'],
            'Authorization': f'Bearer {cfg["api_key"]}',
            'Prefer':        'return=minimal,resolution=merge-duplicates',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status in (200, 201, 204):
                log_ids = [log['id'] for log in logs]
                db.mark_synced(log_ids)
                db.record_sync_log(
                    records_sent=len(daily_records),
                    status='success',
                    error_message=None,
                    synced_by=synced_by,
                    sync_detail=sync_detail,
                )
                return {
                    'success': True,
                    'sent': len(daily_records),
                    'error': None,
                    'status': 'success',
                }
            else:
                resp_body = response.read().decode('utf-8')
                err = f'Supabase returned {response.status}: {resp_body}'
                db.record_sync_log(0, 'failed', err, synced_by, sync_detail=None)
                return {'success': False, 'sent': 0, 'error': err, 'status': 'failed'}

    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8')
        except Exception:
            detail = e.reason
        err = f'HTTP {e.code}: {detail}'
        db.record_sync_log(0, 'failed', err, synced_by)
        return {'success': False, 'sent': 0, 'error': err, 'status': 'failed'}

    except Exception as e:
        err = str(e)
        db.record_sync_log(0, 'failed', err, synced_by)
        return {'success': False, 'sent': 0, 'error': err, 'status': 'failed'}
