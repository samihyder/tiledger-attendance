"""
db_manager.py — Supabase primary data layer.
All reads/writes go directly to Supabase using the service_role key (bypasses RLS).
SQLite is no longer used.
"""

import hashlib
import base64
import json
from datetime import datetime
from config import Config

# ── Supabase client ───────────────────────────────────────────────────────────

_supabase = None

def _sb():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    return _supabase


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    """Flatten embedded PostgREST join dicts into the parent row."""
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


def _one(data: list):
    return data[0] if data else None


# ── Init / seed ───────────────────────────────────────────────────────────────

def init_db():
    """Seed default admin user and shift on first run. Idempotent."""
    sb = _sb()
    if not _one(sb.table('app_users').select('id').eq('username', 'admin').limit(1).execute().data):
        sb.table('app_users').insert({
            'username':      'admin',
            'password_hash': hash_password('admin@2026'),
            'full_name':     'Super Admin',
            'role':          'super_admin',
        }).execute()
    if not _one(sb.table('shifts').select('id').limit(1).execute().data):
        sb.table('shifts').insert({
            'shift_name':    'Morning Shift',
            'shift_start':   '09:00:00',
            'shift_end':     '18:00:00',
            'grace_minutes': 10,
        }).execute()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def get_user(username: str):
    result = _sb().table('app_users').select('*').eq('username', username).eq('active', True).limit(1).execute()
    return _one(result.data)

def update_last_login(user_id: int):
    _sb().table('app_users').update({'last_login': datetime.utcnow().isoformat()}).eq('id', user_id).execute()


# ── Employees ─────────────────────────────────────────────────────────────────

def get_employees(active_only=True):
    q = _sb().table('employees').select('*')
    if active_only:
        q = q.eq('active', True)
    return q.order('full_name').execute().data

def get_employee(employee_id: int):
    return _one(_sb().table('employees').select('*').eq('id', employee_id).limit(1).execute().data)

def get_employee_by_code(code: str):
    return _one(_sb().table('employees').select('*').eq('employee_code', code).limit(1).execute().data)

def auto_deduction_rate(monthly_salary: float) -> float:
    if not monthly_salary or monthly_salary <= 0:
        return 0.0
    return round(monthly_salary / (26 * 9 * 60), 4)

def create_employee(data: dict, created_by: int) -> int:
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = bool(data.get('deduction_rate_override', False))
    rate     = float(data.get('late_deduction_per_minute', 0) or 0) if override else auto_deduction_rate(salary)
    result = _sb().table('employees').insert({
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
    }).execute()
    return result.data[0]['id']

def update_employee(employee_id: int, data: dict):
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = bool(data.get('deduction_rate_override', False))
    rate     = float(data.get('late_deduction_per_minute', 0) or 0) if override else auto_deduction_rate(salary)
    _sb().table('employees').update({
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
    }).eq('id', employee_id).execute()

def delete_employee(employee_id: int):
    _sb().table('employees').update({'active': False}).eq('id', employee_id).execute()


# ── Biometric templates (stub — fingerprint hardware not available on Vercel) ──

def save_template(*args, **kwargs): pass
def get_templates_for_employee(employee_id: int): return []
def get_all_templates(): return []
def delete_template(employee_id: int, finger_index: int): pass


# ── Shifts ────────────────────────────────────────────────────────────────────

def get_shifts(active_only=True):
    q = _sb().table('shifts').select('*')
    if active_only:
        q = q.eq('active', True)
    return q.order('shift_name').execute().data

def get_shift(shift_id: int):
    return _one(_sb().table('shifts').select('*').eq('id', shift_id).limit(1).execute().data)

def create_shift(data: dict) -> int:
    result = _sb().table('shifts').insert({
        'shift_name':    data['shift_name'],
        'shift_start':   data['shift_start'],
        'shift_end':     data['shift_end'],
        'grace_minutes': int(data.get('grace_minutes', Config.DEFAULT_GRACE_MINUTES)),
    }).execute()
    return result.data[0]['id']

def update_shift(shift_id: int, data: dict):
    _sb().table('shifts').update({
        'shift_name':    data['shift_name'],
        'shift_start':   data['shift_start'],
        'shift_end':     data['shift_end'],
        'grace_minutes': int(data.get('grace_minutes', 10)),
        'active':        bool(data.get('active', True)),
    }).eq('id', shift_id).execute()


# ── Rosters ───────────────────────────────────────────────────────────────────

def get_roster_for_date(employee_id: int, roster_date: str):
    result = _sb().table('rosters').select(
        '*, shifts(shift_name, shift_start, shift_end, grace_minutes)'
    ).eq('employee_id', employee_id).eq('roster_date', roster_date).limit(1).execute()
    row = _one(result.data)
    return _flat(row, 'shifts') if row else None

def get_rosters(date_from: str = None, date_to: str = None, employee_id: int = None):
    q = _sb().table('rosters').select(
        '*, employees(full_name, employee_code), shifts(shift_name, shift_start, shift_end, grace_minutes)'
    )
    if date_from:    q = q.gte('roster_date', date_from)
    if date_to:      q = q.lte('roster_date', date_to)
    if employee_id:  q = q.eq('employee_id', employee_id)
    q = q.order('roster_date').order('employee_id')
    return [_flat(r, 'employees', 'shifts') for r in q.execute().data]

def upsert_roster(employee_id: int, shift_id, roster_date: str,
                  is_holiday: bool, notes: str, created_by: int) -> int:
    result = _sb().table('rosters').upsert({
        'employee_id': employee_id,
        'shift_id':    shift_id,
        'roster_date': roster_date,
        'is_holiday':  bool(is_holiday),
        'notes':       notes or None,
        'created_by':  created_by,
    }, on_conflict='employee_id,roster_date').execute()
    return result.data[0]['id']

def save_roster_batch(employee_id: int, entries: list, notes: str, created_by: int):
    rows = [
        {
            'employee_id': employee_id,
            'shift_id':    e.get('shift_id'),
            'roster_date': e['roster_date'],
            'is_holiday':  bool(e.get('is_holiday')),
            'notes':       notes or None,
            'created_by':  created_by,
        }
        for e in entries
    ]
    if rows:
        _sb().table('rosters').upsert(rows, on_conflict='employee_id,roster_date').execute()

def delete_roster(roster_id: int):
    _sb().table('rosters').delete().eq('id', roster_id).execute()


# ── Face templates (128-d embeddings, no images stored) ───────────────────────

def save_face_template(employee_id: int, embedding_json: str, quality: float, enrolled_by: int):
    _sb().table('face_templates').upsert({
        'employee_id': employee_id,
        'embedding':   embedding_json,
        'quality':     quality,
        'enrolled_by': enrolled_by,
        'enrolled_at': datetime.utcnow().isoformat(),
    }, on_conflict='employee_id').execute()

def get_face_template(employee_id: int):
    row = _one(_sb().table('face_templates').select('*').eq('employee_id', employee_id).limit(1).execute().data)
    if row:
        row['enrolled_at'] = _nt(row.get('enrolled_at'))
    return row

def get_all_face_templates():
    result = _sb().table('face_templates').select(
        '*, employees(full_name, employee_code)'
    ).execute()
    return [_flat(r, 'employees') for r in result.data]

def delete_face_template(employee_id: int):
    _sb().table('face_templates').delete().eq('employee_id', employee_id).execute()


# ── Attendance ────────────────────────────────────────────────────────────────

def get_last_punch(employee_id: int, date_str: str):
    result = _sb().table('attendance_logs').select('*').eq(
        'employee_id', employee_id
    ).gte('punch_time', f'{date_str}T00:00:00').lte(
        'punch_time', f'{date_str}T23:59:59'
    ).order('punch_time', desc=True).limit(1).execute()
    row = _one(result.data)
    return _norm_log(row) if row else None

def record_punch(employee_id: int, punch_time: str, punch_type: str,
                 punch_source: str, minutes_late: int, roster_id=None,
                 override_reason: str = None, override_by: int = None) -> int:
    result = _sb().table('attendance_logs').insert({
        'employee_id':    employee_id,
        'punch_time':     punch_time,
        'punch_type':     punch_type,
        'punch_source':   punch_source,
        'minutes_late':   minutes_late,
        'roster_id':      roster_id,
        'override_reason': override_reason,
        'override_by':    override_by,
    }).execute()
    return result.data[0]['id']

def get_attendance_logs(date_from: str = None, date_to: str = None,
                        employee_id: int = None, synced: int = None):
    q = _sb().table('attendance_logs').select('*, employees(full_name, employee_code)')
    if date_from:   q = q.gte('punch_time', f'{date_from}T00:00:00')
    if date_to:     q = q.lte('punch_time', f'{date_to}T23:59:59')
    if employee_id: q = q.eq('employee_id', employee_id)
    if synced is not None: q = q.eq('synced', bool(synced))
    q = q.order('punch_time', desc=True)
    return [_norm_log(r) for r in q.execute().data]

def get_unsynced_logs():
    result = _sb().table('attendance_logs').select(
        '*, employees(full_name, employee_code, department, designation, late_deduction_per_minute)'
    ).eq('synced', False).order('punch_time').limit(Config.SYNC_BATCH_SIZE).execute()
    return [_norm_log(r) for r in result.data]

def edit_punch(log_id: int, new_punch_time: str, edited_by: int):
    _sb().table('attendance_logs').update({
        'punch_time':     new_punch_time,
        'override_by':    edited_by,
        'override_reason': '[edited by admin]',
        'synced':         False,
        'synced_at':      None,
    }).eq('id', log_id).execute()

def update_punch_minutes_late(log_id: int, minutes_late: int):
    _sb().table('attendance_logs').update({'minutes_late': minutes_late}).eq('id', log_id).execute()

def get_punch(log_id: int):
    result = _sb().table('attendance_logs').select(
        '*, employees(full_name, employee_code)'
    ).eq('id', log_id).limit(1).execute()
    row = _one(result.data)
    return _norm_log(row) if row else None

def mark_synced(log_ids: list):
    if not log_ids:
        return
    _sb().table('attendance_logs').update({
        'synced':    True,
        'synced_at': datetime.utcnow().isoformat(),
    }).in_('id', log_ids).execute()

def record_sync_log(records_sent: int, status: str, error_message: str,
                    synced_by: int, sync_detail: str = None):
    _sb().table('sync_log').insert({
        'records_sent':  records_sent,
        'status':        status,
        'error_message': error_message,
        'synced_by':     synced_by,
        'sync_detail':   sync_detail,
    }).execute()

def get_sync_history(limit=20):
    result = _sb().table('sync_log').select(
        '*, app_users(username)'
    ).order('synced_at', desc=True).limit(limit).execute()
    rows = []
    for r in result.data:
        r = _flat(r, 'app_users')
        r['synced_at'] = _nt(r.get('synced_at'))
        rows.append(r)
    return rows


# ── Dashboard stats ───────────────────────────────────────────────────────────

def get_today_stats(date_str: str) -> dict:
    sb = _sb()
    total    = sb.table('employees').select('id', count='exact').eq('active', True).execute().count or 0
    today    = sb.table('attendance_logs').select(
        'employee_id, punch_type, minutes_late'
    ).gte('punch_time', f'{date_str}T00:00:00').lte('punch_time', f'{date_str}T23:59:59').execute().data
    present  = {l['employee_id'] for l in today if l['punch_type'] == 'in'}
    late     = {l['employee_id'] for l in today if l['punch_type'] == 'in' and (l.get('minutes_late') or 0) > 0}
    unsynced = sb.table('attendance_logs').select('id', count='exact').eq('synced', False).execute().count or 0
    return {
        'total_employees': total,
        'present':         len(present),
        'absent':          total - len(present),
        'late':            len(late),
        'unsynced':        unsynced,
    }


# ── App users management ──────────────────────────────────────────────────────

def get_app_users():
    return _sb().table('app_users').select(
        'id, username, full_name, role, active, created_at, last_login'
    ).execute().data

def create_app_user(username: str, password: str, full_name: str, role: str) -> int:
    result = _sb().table('app_users').insert({
        'username':      username,
        'password_hash': hash_password(password),
        'full_name':     full_name,
        'role':          role,
    }).execute()
    return result.data[0]['id']

def update_app_user_password(user_id: int, new_password: str):
    _sb().table('app_users').update({'password_hash': hash_password(new_password)}).eq('id', user_id).execute()

def toggle_app_user(user_id: int, active: bool):
    _sb().table('app_users').update({'active': bool(active)}).eq('id', user_id).execute()


# ── App settings (key-value store) ────────────────────────────────────────────

def get_setting(key: str, default=None):
    row = _one(_sb().table('app_settings').select('value').eq('key', key).limit(1).execute().data)
    return row['value'] if row else default

def set_setting(key: str, value: str):
    _sb().table('app_settings').upsert({'key': key, 'value': value}, on_conflict='key').execute()


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

_ERP_URL_KEY = 'erp_supabase_url'
_ERP_KEY_ENC = 'erp_supabase_key_enc'

# Legacy keys kept for sync settings UI (DB 1 display)
_SB_URL_KEY   = 'supabase_url'
_SB_KEY_ENC   = 'supabase_key_enc'
_SB_TABLE_KEY = 'supabase_table'

def get_sync_settings() -> dict:
    """Returns attendance DB settings (DB 1) — primarily for display."""
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
    sb = _sb()

    employee = _one(sb.table('employees').select('*').eq('id', employee_id).limit(1).execute().data)
    if not employee:
        return {}

    rosters = [
        _flat(r, 'shifts')
        for r in sb.table('rosters').select(
            '*, shifts(shift_name, shift_start, shift_end, grace_minutes)'
        ).eq('employee_id', employee_id).gte('roster_date', date_from).lte(
            'roster_date', date_to
        ).order('roster_date').execute().data
    ]

    logs = [
        _norm_log(r)
        for r in sb.table('attendance_logs').select('*').eq(
            'employee_id', employee_id
        ).gte('punch_time', f'{date_from}T00:00:00').lte(
            'punch_time', f'{date_to}T23:59:59'
        ).order('punch_time').execute().data
    ]

    from collections import defaultdict
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
        first_in   = punch_ins[0]  if punch_ins  else None
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
    overview = []
    for emp in get_employees(active_only=True):
        detail = get_payroll_detail(emp['id'], date_from, date_to)
        if not detail or not detail.get('daily_records'):
            overview.append({
                'employee_id':     emp['id'],
                'employee_code':   emp['employee_code'],
                'full_name':       emp['full_name'],
                'department':      emp.get('department'),
                'working_days':    0, 'present': 0, 'absent': 0, 'holidays': 0,
                'late_days':       0, 'total_late_mins': 0, 'total_deduction': 0,
                'deduction_rate':  float(emp.get('late_deduction_per_minute') or 0),
                'no_roster':       True,
            })
        else:
            overview.append({
                'employee_id':     emp['id'],
                'employee_code':   emp['employee_code'],
                'full_name':       emp['full_name'],
                'department':      emp.get('department') or '',
                'monthly_salary':  float(emp.get('monthly_salary') or 0),
                'weekly_off_day':  int(emp.get('weekly_off_day') or 6),
                'working_days':    detail['working_days'],
                'present':         detail['present'],
                'absent':          detail['absent'],
                'holidays':        detail['holidays'],
                'late_days':       detail['late_days'],
                'total_late_mins': detail['total_late_mins'],
                'total_deduction': detail['total_deduction'],
                'deduction_rate':  detail['deduction_rate'],
                'no_roster':       False,
            })
    return sorted(overview, key=lambda x: x['full_name'])
