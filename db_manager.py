"""
db_manager.py — Supabase data layer via direct REST API (stdlib urllib + json only).
No third-party client libraries — avoids Vercel serverless startup crashes.
"""

import hashlib
import base64
import json
import urllib.request
import urllib.parse
import urllib.error
from collections import defaultdict
from datetime import datetime
from config import Config


# ── REST helpers ──────────────────────────────────────────────────────────────

def _hdr(extra: dict = None) -> dict:
    h = {
        'apikey':        Config.SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {Config.SUPABASE_SERVICE_KEY}',
        'Accept':        'application/json',
    }
    if extra:
        h.update(extra)
    return h


def _pv(v) -> str:
    """Python value → PostgREST filter value string."""
    if v is True:  return 'true'
    if v is False: return 'false'
    if v is None:  return 'null'
    return str(v)


def _get(table: str, select: str = '*', filters=(), order: str = None,
         limit: int = None) -> list:
    """GET rows. filters is a list of (column, 'op.value') tuples."""
    params = [('select', select)] + list(filters)
    if order:  params.append(('order', order))
    if limit:  params.append(('limit', str(limit)))
    url = f'{Config.SUPABASE_URL}/rest/v1/{table}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers=_hdr())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read()) or []


def _one(table: str, select: str = '*', filters=()) -> dict | None:
    rows = _get(table, select, filters, limit=1)
    return rows[0] if rows else None


def _insert(table: str, row: dict) -> dict:
    url = f'{Config.SUPABASE_URL}/rest/v1/{table}'
    req = urllib.request.Request(url, data=json.dumps(row).encode(), method='POST',
        headers=_hdr({'Content-Type': 'application/json',
                      'Prefer':       'return=representation'}))
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())[0]


def _upsert(table: str, data, on_conflict: str = None) -> list:
    qs = f'?on_conflict={urllib.parse.quote(on_conflict)}' if on_conflict else ''
    url = f'{Config.SUPABASE_URL}/rest/v1/{table}{qs}'
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method='POST',
        headers=_hdr({'Content-Type': 'application/json',
                      'Prefer':       'return=representation,resolution=merge-duplicates'}))
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()) or []
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Upsert {table}: {e.code} {e.read().decode()}') from e


def _patch(table: str, data: dict, filters=()) -> None:
    params = urllib.parse.urlencode(list(filters))
    url = f'{Config.SUPABASE_URL}/rest/v1/{table}?{params}'
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method='PATCH',
        headers=_hdr({'Content-Type': 'application/json',
                      'Prefer':       'return=minimal'}))
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


def _delete(table: str, filters=()) -> None:
    params = urllib.parse.urlencode(list(filters))
    url = f'{Config.SUPABASE_URL}/rest/v1/{table}?{params}'
    req = urllib.request.Request(url, method='DELETE', headers=_hdr())
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


# ── Row normalisers ───────────────────────────────────────────────────────────

def _nt(s) -> str:
    """Normalize TIMESTAMPTZ → 'YYYY-MM-DD HH:MM:SS'."""
    if not s:
        return s
    s = str(s).replace('T', ' ')
    for sep in ('+', '.'):
        if sep in s:
            s = s[:s.index(sep)]
    return s.strip()


def _flat(row: dict, *tables: str) -> dict:
    """Flatten embedded PostgREST join objects into the parent row."""
    row = dict(row)
    for t in tables:
        if isinstance(row.get(t), dict):
            row.update(row.pop(t))
        elif t in row:
            del row[t]
    return row


def _norm_log(row: dict) -> dict:
    row = _flat(row, 'employees')
    for f in ('punch_time', 'created_at', 'synced_at'):
        if f in row:
            row[f] = _nt(row[f])
    return row


# ── Init / seed ───────────────────────────────────────────────────────────────

def init_db():
    """Seed default admin user and shift on first run. Non-fatal.
    Skipped on Vercel — schema_supabase.sql already seeds the defaults."""
    import os
    if os.environ.get('VERCEL'):
        return
    try:
        if not _one('app_users', 'id', [('username', 'eq.admin')]):
            _insert('app_users', {
                'username':      'admin',
                'password_hash': hash_password('admin@2026'),
                'full_name':     'Super Admin',
                'role':          'super_admin',
            })
        if not _get('shifts', 'id', limit=1):
            _insert('shifts', {
                'shift_name':    'Morning Shift',
                'shift_start':   '09:00:00',
                'shift_end':     '18:00:00',
                'grace_minutes': 10,
            })
    except Exception as e:
        print(f'[WARN] DB init skipped: {e}')


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def get_user(username: str):
    return _one('app_users', '*',
                [('username', f'eq.{username}'), ('active', 'eq.true')])

def update_last_login(user_id: int):
    _patch('app_users', {'last_login': datetime.utcnow().isoformat()},
           [('id', f'eq.{user_id}')])


# ── Employees ─────────────────────────────────────────────────────────────────

def get_employees(active_only=True):
    filters = [('active', 'eq.true')] if active_only else []
    return _get('employees', '*', filters, order='full_name')

def get_employee(employee_id: int):
    return _one('employees', '*', [('id', f'eq.{employee_id}')])

def get_employee_by_code(code: str):
    return _one('employees', '*', [('employee_code', f'eq.{code}')])

def auto_deduction_rate(monthly_salary: float) -> float:
    if not monthly_salary or monthly_salary <= 0:
        return 0.0
    return round(monthly_salary / (26 * 9 * 60), 4)

def create_employee(data: dict, created_by: int) -> int:
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = bool(data.get('deduction_rate_override', False))
    rate     = float(data.get('late_deduction_per_minute', 0) or 0) if override else auto_deduction_rate(salary)
    row = _insert('employees', {
        'employee_code':             data['employee_code'],
        'full_name':                 data['full_name'],
        'department':                data.get('department') or None,
        'designation':               data.get('designation') or None,
        'phone':                     data.get('phone') or None,
        'email':                     data.get('email') or None,
        'joining_date':              data.get('joining_date') or None,
        'monthly_salary':            salary,
        'weekly_off_day':            int(data.get('weekly_off_day', 6)),
        'late_deduction_per_minute': rate,
        'deduction_rate_override':   override,
        'created_by':                created_by,
    })
    return row['id']

def update_employee(employee_id: int, data: dict):
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = bool(data.get('deduction_rate_override', False))
    rate     = float(data.get('late_deduction_per_minute', 0) or 0) if override else auto_deduction_rate(salary)
    _patch('employees', {
        'full_name':                 data['full_name'],
        'department':                data.get('department') or None,
        'designation':               data.get('designation') or None,
        'phone':                     data.get('phone') or None,
        'email':                     data.get('email') or None,
        'joining_date':              data.get('joining_date') or None,
        'monthly_salary':            salary,
        'weekly_off_day':            int(data.get('weekly_off_day', 6)),
        'late_deduction_per_minute': rate,
        'deduction_rate_override':   override,
        'active':                    bool(data.get('active', True)),
    }, [('id', f'eq.{employee_id}')])

def delete_employee(employee_id: int):
    _patch('employees', {'active': False}, [('id', f'eq.{employee_id}')])


# ── Biometric templates (stub — fingerprint hardware not on Vercel) ────────────

def save_template(*args, **kwargs): pass
def get_templates_for_employee(employee_id: int): return []
def get_all_templates(): return []
def delete_template(employee_id: int, finger_index: int): pass


# ── Shifts ────────────────────────────────────────────────────────────────────

def get_shifts(active_only=True):
    filters = [('active', 'eq.true')] if active_only else []
    return _get('shifts', '*', filters, order='shift_name')

def get_shift(shift_id: int):
    return _one('shifts', '*', [('id', f'eq.{shift_id}')])

def create_shift(data: dict) -> int:
    row = _insert('shifts', {
        'shift_name':    data['shift_name'],
        'shift_start':   data['shift_start'],
        'shift_end':     data['shift_end'],
        'grace_minutes': int(data.get('grace_minutes', Config.DEFAULT_GRACE_MINUTES)),
    })
    return row['id']

def update_shift(shift_id: int, data: dict):
    _patch('shifts', {
        'shift_name':    data['shift_name'],
        'shift_start':   data['shift_start'],
        'shift_end':     data['shift_end'],
        'grace_minutes': int(data.get('grace_minutes', 10)),
        'active':        bool(data.get('active', True)),
    }, [('id', f'eq.{shift_id}')])


# ── Rosters ───────────────────────────────────────────────────────────────────

def get_roster_for_date(employee_id: int, roster_date: str):
    rows = _get('rosters', '*,shifts(shift_name,shift_start,shift_end,grace_minutes)',
                [('employee_id', f'eq.{employee_id}'), ('roster_date', f'eq.{roster_date}')],
                limit=1)
    return _flat(rows[0], 'shifts') if rows else None

def get_rosters(date_from: str = None, date_to: str = None, employee_id: int = None):
    f = []
    if date_from:    f.append(('roster_date', f'gte.{date_from}'))
    if date_to:      f.append(('roster_date', f'lte.{date_to}'))
    if employee_id:  f.append(('employee_id', f'eq.{employee_id}'))
    rows = _get('rosters',
                '*,employees(full_name,employee_code),shifts(shift_name,shift_start,shift_end,grace_minutes)',
                f, order='roster_date,employee_id')
    return [_flat(r, 'employees', 'shifts') for r in rows]

def upsert_roster(employee_id: int, shift_id, roster_date: str,
                  is_holiday: bool, notes: str, created_by: int) -> int:
    rows = _upsert('rosters', {
        'employee_id': employee_id,
        'shift_id':    shift_id,
        'roster_date': roster_date,
        'is_holiday':  bool(is_holiday),
        'notes':       notes or None,
        'created_by':  created_by,
    }, on_conflict='employee_id,roster_date')
    return rows[0]['id'] if rows else 0

def save_roster_batch(employee_id: int, entries: list, notes: str, created_by: int):
    rows = [{
        'employee_id': employee_id,
        'shift_id':    e.get('shift_id'),
        'roster_date': e['roster_date'],
        'is_holiday':  bool(e.get('is_holiday')),
        'notes':       notes or None,
        'created_by':  created_by,
    } for e in entries]
    if rows:
        _upsert('rosters', rows, on_conflict='employee_id,roster_date')

def delete_roster(roster_id: int):
    _delete('rosters', [('id', f'eq.{roster_id}')])


# ── Face templates ────────────────────────────────────────────────────────────

def save_face_template(employee_id: int, embedding_json: str, quality: float, enrolled_by: int):
    _upsert('face_templates', {
        'employee_id': employee_id,
        'embedding':   embedding_json,
        'quality':     quality,
        'enrolled_by': enrolled_by,
        'enrolled_at': datetime.utcnow().isoformat(),
    }, on_conflict='employee_id')

def get_face_template(employee_id: int):
    row = _one('face_templates', '*', [('employee_id', f'eq.{employee_id}')])
    if row:
        row['enrolled_at'] = _nt(row.get('enrolled_at'))
    return row

def get_all_face_templates():
    rows = _get('face_templates', '*,employees(full_name,employee_code)')
    return [_flat(r, 'employees') for r in rows]

def delete_face_template(employee_id: int):
    _delete('face_templates', [('employee_id', f'eq.{employee_id}')])


# ── Attendance ────────────────────────────────────────────────────────────────

def get_last_punch(employee_id: int, date_str: str):
    rows = _get('attendance_logs', '*',
                [('employee_id', f'eq.{employee_id}'),
                 ('punch_time',  f'gte.{date_str}T00:00:00'),
                 ('punch_time',  f'lte.{date_str}T23:59:59')],
                order='punch_time.desc', limit=1)
    return _norm_log(rows[0]) if rows else None

def record_punch(employee_id: int, punch_time: str, punch_type: str,
                 punch_source: str, minutes_late: int, roster_id=None,
                 override_reason: str = None, override_by: int = None) -> int:
    row = _insert('attendance_logs', {
        'employee_id':    employee_id,
        'punch_time':     punch_time,
        'punch_type':     punch_type,
        'punch_source':   punch_source,
        'minutes_late':   minutes_late,
        'roster_id':      roster_id,
        'override_reason': override_reason,
        'override_by':    override_by,
    })
    return row['id']

def get_attendance_logs(date_from: str = None, date_to: str = None,
                        employee_id: int = None, synced: int = None):
    f = []
    if date_from:   f.append(('punch_time', f'gte.{date_from}T00:00:00'))
    if date_to:     f.append(('punch_time', f'lte.{date_to}T23:59:59'))
    if employee_id: f.append(('employee_id', f'eq.{employee_id}'))
    if synced is not None: f.append(('synced', f'eq.{_pv(bool(synced))}'))
    rows = _get('attendance_logs', '*,employees(full_name,employee_code)',
                f, order='punch_time.desc')
    return [_norm_log(r) for r in rows]

def get_unsynced_logs():
    rows = _get('attendance_logs',
                '*,employees(full_name,employee_code,department,designation,late_deduction_per_minute)',
                [('synced', 'eq.false')], order='punch_time',
                limit=Config.SYNC_BATCH_SIZE)
    return [_norm_log(r) for r in rows]

def edit_punch(log_id: int, new_punch_time: str, edited_by: int):
    _patch('attendance_logs', {
        'punch_time':     new_punch_time,
        'override_by':    edited_by,
        'override_reason': '[edited by admin]',
        'synced':         False,
        'synced_at':      None,
    }, [('id', f'eq.{log_id}')])

def update_punch_minutes_late(log_id: int, minutes_late: int):
    _patch('attendance_logs', {'minutes_late': minutes_late}, [('id', f'eq.{log_id}')])

def get_punch(log_id: int):
    rows = _get('attendance_logs', '*,employees(full_name,employee_code)',
                [('id', f'eq.{log_id}')], limit=1)
    return _norm_log(rows[0]) if rows else None

def mark_synced(log_ids: list):
    if not log_ids:
        return
    ids_str = ','.join(str(i) for i in log_ids)
    _patch('attendance_logs',
           {'synced': True, 'synced_at': datetime.utcnow().isoformat()},
           [('id', f'in.({ids_str})')])

def record_sync_log(records_sent: int, status: str, error_message: str,
                    synced_by: int, sync_detail: str = None):
    _insert('sync_log', {
        'records_sent':  records_sent,
        'status':        status,
        'error_message': error_message,
        'synced_by':     synced_by,
        'sync_detail':   sync_detail,
    })

def get_sync_history(limit=20):
    rows = _get('sync_log', '*,app_users(username)',
                order='synced_at.desc', limit=limit)
    result = []
    for r in rows:
        r = _flat(r, 'app_users')
        r['synced_at'] = _nt(r.get('synced_at'))
        result.append(r)
    return result


# ── Dashboard stats ───────────────────────────────────────────────────────────

def get_today_stats(date_str: str) -> dict:
    emp_rows  = _get('employees', 'id', [('active', 'eq.true')])
    total     = len(emp_rows)
    today_logs = _get('attendance_logs', 'employee_id,punch_type,minutes_late',
                      [('punch_time', f'gte.{date_str}T00:00:00'),
                       ('punch_time', f'lte.{date_str}T23:59:59')])
    present  = {l['employee_id'] for l in today_logs if l['punch_type'] == 'in'}
    late     = {l['employee_id'] for l in today_logs
                if l['punch_type'] == 'in' and (l.get('minutes_late') or 0) > 0}
    unsynced_rows = _get('attendance_logs', 'id', [('synced', 'eq.false')])
    return {
        'total_employees': total,
        'present':         len(present),
        'absent':          total - len(present),
        'late':            len(late),
        'unsynced':        len(unsynced_rows),
    }


# ── App users management ──────────────────────────────────────────────────────

def get_app_users():
    return _get('app_users', 'id,username,full_name,role,active,created_at,last_login')

def create_app_user(username: str, password: str, full_name: str, role: str) -> int:
    row = _insert('app_users', {
        'username':      username,
        'password_hash': hash_password(password),
        'full_name':     full_name,
        'role':          role,
    })
    return row['id']

def update_app_user_password(user_id: int, new_password: str):
    _patch('app_users', {'password_hash': hash_password(new_password)},
           [('id', f'eq.{user_id}')])

def toggle_app_user(user_id: int, active: bool):
    _patch('app_users', {'active': bool(active)}, [('id', f'eq.{user_id}')])


# ── App settings (key-value store) ────────────────────────────────────────────

def get_setting(key: str, default=None):
    row = _one('app_settings', 'value', [('key', f'eq.{key}')])
    return row['value'] if row else default

def set_setting(key: str, value: str):
    _upsert('app_settings', {'key': key, 'value': value}, on_conflict='key')


# ── Encrypted settings (XOR-cipher for API keys stored in app_settings) ───────

def _enc_key() -> bytes:
    return hashlib.sha256(Config.SECRET_KEY.encode('utf-8')).digest()

def encrypt_setting(plaintext: str) -> str:
    if not plaintext:
        return ''
    key  = _enc_key()
    data = plaintext.encode('utf-8')
    enc  = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(enc).decode('ascii')

def decrypt_setting(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    key  = _enc_key()
    data = base64.urlsafe_b64decode(ciphertext.encode('ascii'))
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).decode('utf-8')


# ── ERP Supabase sync settings (DB 2) ─────────────────────────────────────────

_SB_URL_KEY   = 'supabase_url'
_SB_KEY_ENC   = 'supabase_key_enc'
_SB_TABLE_KEY = 'supabase_table'
_ERP_URL_KEY  = 'erp_supabase_url'
_ERP_KEY_ENC  = 'erp_supabase_key_enc'

def get_sync_settings() -> dict:
    url     = get_setting(_SB_URL_KEY)   or Config.SUPABASE_URL
    key_enc = get_setting(_SB_KEY_ENC)
    api_key = decrypt_setting(key_enc) if key_enc else Config.SUPABASE_KEY
    table   = get_setting(_SB_TABLE_KEY) or Config.SUPABASE_TABLE
    return {'url': url, 'api_key': api_key, 'table': table}

def save_sync_settings(url: str, api_key: str, table: str):
    set_setting(_SB_URL_KEY,   url.strip())
    set_setting(_SB_KEY_ENC,   encrypt_setting(api_key.strip()))
    set_setting(_SB_TABLE_KEY, table.strip())

def get_sync_settings_display() -> dict:
    url     = get_setting(_SB_URL_KEY)   or Config.SUPABASE_URL
    key_enc = get_setting(_SB_KEY_ENC)   or ''
    table   = get_setting(_SB_TABLE_KEY) or Config.SUPABASE_TABLE
    return {'url': url, 'api_key_enc': key_enc, 'table': table}

def get_erp_sync_settings() -> dict:
    url     = get_setting(_ERP_URL_KEY)  or Config.ERP_SUPABASE_URL
    key_enc = get_setting(_ERP_KEY_ENC)
    api_key = decrypt_setting(key_enc) if key_enc else Config.ERP_SUPABASE_SERVICE_KEY
    return {'url': url, 'api_key': api_key}

def save_erp_sync_settings(url: str, api_key: str):
    set_setting(_ERP_URL_KEY, url.strip())
    set_setting(_ERP_KEY_ENC, encrypt_setting(api_key.strip()))

def get_erp_sync_settings_display() -> dict:
    url     = get_setting(_ERP_URL_KEY) or Config.ERP_SUPABASE_URL
    key_enc = get_setting(_ERP_KEY_ENC) or ''
    return {'url': url, 'api_key_enc': key_enc}


# ── Manual mode ───────────────────────────────────────────────────────────────

MANUAL_MODE_KEY = 'manual_mode_date'

def get_manual_mode_date() -> str | None:
    return get_setting(MANUAL_MODE_KEY)

def enable_manual_mode(date_str: str):
    set_setting(MANUAL_MODE_KEY, date_str)

def disable_manual_mode():
    set_setting(MANUAL_MODE_KEY, '')


# ── Payroll ───────────────────────────────────────────────────────────────────

def get_payroll_detail(employee_id: int, date_from: str, date_to: str) -> dict:
    employee = _one('employees', '*', [('id', f'eq.{employee_id}')])
    if not employee:
        return {}

    roster_rows = _get('rosters',
                       '*,shifts(shift_name,shift_start,shift_end,grace_minutes)',
                       [('employee_id', f'eq.{employee_id}'),
                        ('roster_date', f'gte.{date_from}'),
                        ('roster_date', f'lte.{date_to}')],
                       order='roster_date')
    rosters = [_flat(r, 'shifts') for r in roster_rows]

    log_rows = _get('attendance_logs', '*',
                    [('employee_id', f'eq.{employee_id}'),
                     ('punch_time',  f'gte.{date_from}T00:00:00'),
                     ('punch_time',  f'lte.{date_to}T23:59:59')],
                    order='punch_time')
    logs = [_norm_log(r) for r in log_rows]

    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log['punch_time'][:10]].append(log)

    rate = float(employee.get('late_deduction_per_minute') or 0)
    daily_records = []

    for roster in rosters:
        date_str   = roster['roster_date']
        is_holiday = bool(roster.get('is_holiday'))
        day_logs   = logs_by_date.get(date_str, [])
        punch_ins  = [l for l in day_logs if l['punch_type'] == 'in']
        punch_outs = [l for l in day_logs if l['punch_type'] == 'out']
        first_in   = punch_ins[0]   if punch_ins  else None
        last_out   = punch_outs[-1] if punch_outs else None

        status       = 'Holiday' if is_holiday else ('Present' if first_in else 'Absent')
        minutes_late = first_in['minutes_late'] if first_in else 0

        hours_worked = None
        if first_in and last_out:
            t_in  = datetime.strptime(first_in['punch_time'],  '%Y-%m-%d %H:%M:%S')
            t_out = datetime.strptime(last_out['punch_time'],  '%Y-%m-%d %H:%M:%S')
            hours_worked = round((t_out - t_in).total_seconds() / 3600, 2)

        daily_records.append({
            'date':            date_str,
            'shift_name':      roster.get('shift_name'),
            'shift_start':     roster.get('shift_start'),
            'is_holiday':      is_holiday,
            'status':          status,
            'punch_in':        first_in['punch_time'][11:16]  if first_in  else None,
            'punch_out':       last_out['punch_time'][11:16]  if last_out  else None,
            'hours_worked':    hours_worked,
            'minutes_late':    minutes_late,
            'daily_deduction': round(minutes_late * rate, 2),
            'punch_source':    first_in['punch_source'] if first_in else None,
        })

    return {
        'employee':        employee,
        'date_from':       date_from,
        'date_to':         date_to,
        'daily_records':   daily_records,
        'working_days':    sum(1 for r in daily_records if not r['is_holiday']),
        'present':         sum(1 for r in daily_records if r['status'] == 'Present'),
        'absent':          sum(1 for r in daily_records if r['status'] == 'Absent'),
        'holidays':        sum(1 for r in daily_records if r['status'] == 'Holiday'),
        'late_days':       sum(1 for r in daily_records if r['minutes_late'] > 0),
        'total_late_mins': sum(r['minutes_late'] for r in daily_records),
        'total_deduction': round(sum(r['daily_deduction'] for r in daily_records), 2),
        'deduction_rate':  rate,
    }


def get_payroll_overview(date_from: str, date_to: str) -> list:
    employees = get_employees(active_only=True)
    if not employees:
        return []

    # 3 bulk queries instead of 1 + N*3
    roster_rows = _get('rosters',
                       'employee_id,roster_date,is_holiday',
                       [('roster_date', f'gte.{date_from}'),
                        ('roster_date', f'lte.{date_to}')],
                       order='roster_date')
    rosters_by_emp = defaultdict(list)
    for r in roster_rows:
        rosters_by_emp[r['employee_id']].append(r)

    log_rows = _get('attendance_logs',
                    'employee_id,punch_type,punch_time,minutes_late',
                    [('punch_time', f'gte.{date_from}T00:00:00'),
                     ('punch_time', f'lte.{date_to}T23:59:59')],
                    order='punch_time')
    logs_by_emp = defaultdict(list)
    for log in log_rows:
        log['punch_time'] = _nt(log['punch_time'])
        logs_by_emp[log['employee_id']].append(log)

    overview = []
    for emp in employees:
        emp_id   = emp['id']
        rate     = float(emp.get('late_deduction_per_minute') or 0)
        rosters  = rosters_by_emp.get(emp_id, [])
        emp_logs = logs_by_emp.get(emp_id, [])

        if not rosters:
            overview.append({
                'employee_id':   emp_id, 'employee_code': emp['employee_code'],
                'full_name':     emp['full_name'], 'department': emp.get('department'),
                'working_days':  0, 'present': 0, 'absent': 0, 'holidays': 0,
                'late_days':     0, 'total_late_mins': 0, 'total_deduction': 0,
                'deduction_rate': rate, 'no_roster': True,
            })
            continue

        logs_by_date = defaultdict(list)
        for log in emp_logs:
            logs_by_date[log['punch_time'][:10]].append(log)

        working_days = present = absent = holidays = late_days = 0
        total_late_mins = 0
        total_deduction = 0.0

        for roster in rosters:
            is_holiday = bool(roster.get('is_holiday'))
            punch_ins  = [l for l in logs_by_date.get(roster['roster_date'], [])
                          if l['punch_type'] == 'in']
            if is_holiday:
                holidays += 1
            else:
                working_days += 1
                if punch_ins:
                    present += 1
                    mins = int(punch_ins[0].get('minutes_late') or 0)
                    if mins > 0:
                        late_days      += 1
                        total_late_mins += mins
                        total_deduction += mins * rate
                else:
                    absent += 1

        overview.append({
            'employee_id':     emp_id, 'employee_code':  emp['employee_code'],
            'full_name':       emp['full_name'], 'department': emp.get('department') or '',
            'monthly_salary':  float(emp.get('monthly_salary') or 0),
            'weekly_off_day':  int(emp.get('weekly_off_day') or 6),
            'working_days':    working_days, 'present':         present,
            'absent':          absent,        'holidays':        holidays,
            'late_days':       late_days,     'total_late_mins': total_late_mins,
            'total_deduction': round(total_deduction, 2),
            'deduction_rate':  rate, 'no_roster': False,
        })

    return sorted(overview, key=lambda x: x['full_name'])
