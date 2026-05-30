from __future__ import annotations

import sqlite3
import hashlib
import base64
import os
from contextlib import contextmanager
from config import Config

# ──────────────────────────────────────────────────────────────────────────────
# Backend selection
# DATABASE_URL set  → PostgreSQL (Supabase) — Vercel / cloud deployment
# DATABASE_URL unset → SQLite               — local punch station
# ──────────────────────────────────────────────────────────────────────────────

_DATABASE_URL = Config.DATABASE_URL
_USE_POSTGRES = bool(_DATABASE_URL)

# ── PostgreSQL adapter ────────────────────────────────────────────────────────

class _PGCursor:
    """Thin wrapper around psycopg2 RealDictCursor that mimics sqlite3 cursor."""
    def __init__(self, cur):
        self._cur      = cur
        self.lastrowid = None

    def fetchone(self):  return self._cur.fetchone()
    def fetchall(self):  return self._cur.fetchall()

    @property
    def rowcount(self):  return self._cur.rowcount


class _PGConn:
    """Wraps a psycopg2 connection to look like sqlite3 for this codebase."""

    _REPLACE = staticmethod(lambda sql: (
        sql
        .replace('?',             '%s')
        .replace("datetime('now')", 'NOW()')
        .replace('datetime("now")', 'NOW()')
        .replace("date('now')",   'CURRENT_DATE')
    ))

    def __init__(self, pgconn):
        self._conn = pgconn

    def execute(self, sql, params=()):
        adapted   = self._REPLACE(sql)
        is_insert = adapted.strip().upper().startswith('INSERT')

        # Append RETURNING id to every INSERT so callers can read lastrowid.
        # All tables in schema_supabase.sql have a BIGINT GENERATED id column.
        if is_insert and 'RETURNING' not in adapted.upper():
            adapted = adapted.rstrip('; \n') + ' RETURNING id'

        cur = self._conn.cursor()
        cur.execute(adapted, params or None)
        proxy = _PGCursor(cur)

        if is_insert:
            try:
                row = cur.fetchone()
                proxy.lastrowid = row['id'] if row else None
            except Exception:
                proxy.lastrowid = None

        return proxy

    def executescript(self, _script):
        pass  # Tables are managed directly in Supabase SQL editor

    def commit(self):   self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):    self._conn.close()


# ── SQLite connection ─────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


# ── Unified context manager ───────────────────────────────────────────────────

@contextmanager
def db():
    if _USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        pgconn  = psycopg2.connect(_DATABASE_URL,
                                   cursor_factory=psycopg2.extras.RealDictCursor)
        # Isolate all attendance tables in their own schema — no collision with ERP's public schema
        pgconn.cursor().execute('SET search_path TO attendance, public')
        wrapper = _PGConn(pgconn)
        try:
            yield wrapper
            pgconn.commit()
        except Exception:
            pgconn.rollback()
            raise
        finally:
            pgconn.close()
    else:
        conn = get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# ──────────────────────────────────────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS app_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('super_admin', 'manager', 'system_admin', 'store')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code             TEXT UNIQUE NOT NULL,
    full_name                 TEXT NOT NULL,
    department                TEXT,
    designation               TEXT,
    phone                     TEXT,
    email                     TEXT,
    joining_date              TEXT,
    monthly_salary            REAL NOT NULL DEFAULT 0,
    weekly_off_day            INTEGER NOT NULL DEFAULT 6,  -- 0=Mon…6=Sun (Python weekday)
    late_deduction_per_minute REAL NOT NULL DEFAULT 0,
    deduction_rate_override   INTEGER NOT NULL DEFAULT 0,  -- 1=manually set, 0=auto
    active                    INTEGER NOT NULL DEFAULT 1,
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    created_by                INTEGER REFERENCES app_users(id)
);

CREATE TABLE IF NOT EXISTS biometric_templates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    finger_index  INTEGER NOT NULL,
    finger_label  TEXT NOT NULL,
    template_data BLOB NOT NULL,
    quality_score INTEGER,
    enrolled_at   TEXT NOT NULL DEFAULT (datetime('now')),
    enrolled_by   INTEGER REFERENCES app_users(id),
    UNIQUE(employee_id, finger_index)
);

CREATE TABLE IF NOT EXISTS shifts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_name     TEXT NOT NULL,
    shift_start    TEXT NOT NULL,
    shift_end      TEXT NOT NULL,
    grace_minutes  INTEGER NOT NULL DEFAULT 10,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rosters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    shift_id    INTEGER REFERENCES shifts(id),
    roster_date TEXT NOT NULL,
    is_holiday  INTEGER NOT NULL DEFAULT 0,
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    created_by  INTEGER REFERENCES app_users(id),
    UNIQUE(employee_id, roster_date)
);

CREATE TABLE IF NOT EXISTS face_templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    embedding   TEXT NOT NULL,      -- JSON array of 128 floats; NO image stored
    quality     REAL,               -- anti-spoofing score at enrollment time
    enrolled_at TEXT NOT NULL DEFAULT (datetime('now')),
    enrolled_by INTEGER REFERENCES app_users(id),
    UNIQUE(employee_id)             -- one face template per employee
);

CREATE TABLE IF NOT EXISTS attendance_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(id),
    punch_time      TEXT NOT NULL,
    punch_type      TEXT NOT NULL CHECK(punch_type IN ('in', 'out')),
    punch_source    TEXT NOT NULL DEFAULT 'biometric'
                        CHECK(punch_source IN ('biometric', 'manual')),
    minutes_late    INTEGER NOT NULL DEFAULT 0,
    roster_id       INTEGER REFERENCES rosters(id),
    override_reason TEXT,
    override_by     INTEGER REFERENCES app_users(id),
    synced          INTEGER NOT NULL DEFAULT 0,
    synced_at       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_attendance_employee_date
    ON attendance_logs(employee_id, punch_time);
CREATE INDEX IF NOT EXISTS idx_attendance_synced
    ON attendance_logs(synced) WHERE synced = 0;

CREATE TABLE IF NOT EXISTS sync_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    synced_at      TEXT NOT NULL DEFAULT (datetime('now')),
    records_sent   INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL CHECK(status IN ('success', 'failed', 'partial')),
    error_message  TEXT,
    synced_by      INTEGER REFERENCES app_users(id)
);
"""

def _run_migrations(conn: sqlite3.Connection):
    """Idempotent column additions for existing databases."""
    migrations = [
        ('employees', 'late_deduction_per_minute', 'REAL NOT NULL DEFAULT 0'),
        ('employees', 'monthly_salary',            'REAL NOT NULL DEFAULT 0'),
        ('employees', 'weekly_off_day',            'INTEGER NOT NULL DEFAULT 6'),
        ('employees', 'deduction_rate_override',   'INTEGER NOT NULL DEFAULT 0'),
        ('rosters',   'is_holiday',                'INTEGER NOT NULL DEFAULT 0'),
        ('sync_log',  'sync_detail',               'TEXT'),
    ]
    for table, column, definition in migrations:
        try:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
        except sqlite3.OperationalError:
            pass  # column already exists

def init_db():
    if _USE_POSTGRES:
        # Schema is managed in Supabase. Only seed the default admin user.
        with db() as conn:
            _seed_defaults(conn)
    else:
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
        with db() as conn:
            conn.executescript(SCHEMA)
            _run_migrations(conn)
            _seed_defaults(conn)

def _seed_defaults(conn: sqlite3.Connection):
    # Default super admin (change password immediately after first login)
    existing = conn.execute('SELECT id FROM app_users WHERE username = ?', ('admin',)).fetchone()
    if not existing:
        conn.execute(
            'INSERT INTO app_users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
            ('admin', hash_password('admin@2026'), 'Super Admin', 'super_admin')
        )

    # Default shift
    existing_shift = conn.execute('SELECT id FROM shifts LIMIT 1').fetchone()
    if not existing_shift:
        conn.execute(
            'INSERT INTO shifts (shift_name, shift_start, shift_end, grace_minutes) VALUES (?, ?, ?, ?)',
            ('Morning Shift', '09:00', '18:00', 10)
        )

# ──────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ──────────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def get_user(username: str):
    with db() as conn:
        return conn.execute(
            'SELECT * FROM app_users WHERE username = ? AND active = 1', (username,)
        ).fetchone()

def update_last_login(user_id: int):
    with db() as conn:
        conn.execute(
            "UPDATE app_users SET last_login = datetime('now') WHERE id = ?", (user_id,)
        )

# ──────────────────────────────────────────────────────────────────────────────
# Employees
# ──────────────────────────────────────────────────────────────────────────────

def get_employees(active_only=True):
    with db() as conn:
        q = 'SELECT * FROM employees'
        if active_only:
            q += ' WHERE active = 1'
        q += ' ORDER BY full_name'
        return conn.execute(q).fetchall()

def get_employee(employee_id: int):
    with db() as conn:
        return conn.execute('SELECT * FROM employees WHERE id = ?', (employee_id,)).fetchone()

def get_employee_by_code(code: str):
    with db() as conn:
        return conn.execute('SELECT * FROM employees WHERE employee_code = ?', (code,)).fetchone()

def auto_deduction_rate(monthly_salary: float) -> float:
    """Calculate per-minute late deduction from monthly salary.
    Assumes 26 working days/month × 9 hours/day × 60 min = 14,040 min/month.
    """
    if not monthly_salary or monthly_salary <= 0:
        return 0.0
    return round(monthly_salary / (26 * 9 * 60), 4)

def create_employee(data: dict, created_by: int) -> int:
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = int(bool(data.get('deduction_rate_override', False)))
    if override:
        rate = float(data.get('late_deduction_per_minute', 0) or 0)
    else:
        rate = auto_deduction_rate(salary)

    with db() as conn:
        cur = conn.execute(
            '''INSERT INTO employees
               (employee_code, full_name, department, designation, phone, email,
                joining_date, monthly_salary, weekly_off_day,
                late_deduction_per_minute, deduction_rate_override, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (data['employee_code'], data['full_name'], data.get('department'),
             data.get('designation'), data.get('phone'), data.get('email'),
             data.get('joining_date'), salary,
             int(data.get('weekly_off_day', 6)),
             rate, override, created_by)
        )
        return cur.lastrowid

def update_employee(employee_id: int, data: dict):
    salary   = float(data.get('monthly_salary', 0) or 0)
    override = int(bool(data.get('deduction_rate_override', False)))
    if override:
        rate = float(data.get('late_deduction_per_minute', 0) or 0)
    else:
        rate = auto_deduction_rate(salary)

    with db() as conn:
        conn.execute(
            '''UPDATE employees
               SET full_name=?, department=?, designation=?, phone=?, email=?,
                   joining_date=?, monthly_salary=?, weekly_off_day=?,
                   late_deduction_per_minute=?, deduction_rate_override=?, active=?
               WHERE id=?''',
            (data['full_name'], data.get('department'), data.get('designation'),
             data.get('phone'), data.get('email'), data.get('joining_date'),
             salary, int(data.get('weekly_off_day', 6)),
             rate, override,
             1 if data.get('active', True) else 0, employee_id)
        )

def delete_employee(employee_id: int):
    with db() as conn:
        conn.execute('UPDATE employees SET active = 0 WHERE id = ?', (employee_id,))

# ──────────────────────────────────────────────────────────────────────────────
# Biometric templates
# ──────────────────────────────────────────────────────────────────────────────

def save_template(employee_id: int, finger_index: int, finger_label: str,
                  template_data: bytes, quality_score: int, enrolled_by: int):
    with db() as conn:
        conn.execute(
            '''INSERT INTO biometric_templates
               (employee_id, finger_index, finger_label, template_data, quality_score, enrolled_by)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(employee_id, finger_index)
               DO UPDATE SET template_data=excluded.template_data,
                             quality_score=excluded.quality_score,
                             enrolled_at=datetime('now'),
                             enrolled_by=excluded.enrolled_by''',
            (employee_id, finger_index, finger_label, template_data, quality_score, enrolled_by)
        )

def get_templates_for_employee(employee_id: int):
    with db() as conn:
        return conn.execute(
            'SELECT * FROM biometric_templates WHERE employee_id = ?', (employee_id,)
        ).fetchall()

def get_all_templates():
    """Load all enrolled templates for 1:N identification."""
    with db() as conn:
        return conn.execute(
            '''SELECT bt.*, e.full_name, e.employee_code
               FROM biometric_templates bt
               JOIN employees e ON e.id = bt.employee_id
               WHERE e.active = 1'''
        ).fetchall()

def delete_template(employee_id: int, finger_index: int):
    with db() as conn:
        conn.execute(
            'DELETE FROM biometric_templates WHERE employee_id = ? AND finger_index = ?',
            (employee_id, finger_index)
        )

# ──────────────────────────────────────────────────────────────────────────────
# Shifts
# ──────────────────────────────────────────────────────────────────────────────

def get_shifts(active_only=True):
    with db() as conn:
        q = 'SELECT * FROM shifts'
        if active_only:
            q += ' WHERE active = 1'
        return conn.execute(q + ' ORDER BY shift_name').fetchall()

def get_shift(shift_id: int):
    with db() as conn:
        return conn.execute('SELECT * FROM shifts WHERE id = ?', (shift_id,)).fetchone()

def create_shift(data: dict) -> int:
    with db() as conn:
        cur = conn.execute(
            'INSERT INTO shifts (shift_name, shift_start, shift_end, grace_minutes) VALUES (?, ?, ?, ?)',
            (data['shift_name'], data['shift_start'], data['shift_end'],
             int(data.get('grace_minutes', Config.DEFAULT_GRACE_MINUTES)))
        )
        return cur.lastrowid

def update_shift(shift_id: int, data: dict):
    with db() as conn:
        conn.execute(
            'UPDATE shifts SET shift_name=?, shift_start=?, shift_end=?, grace_minutes=?, active=? WHERE id=?',
            (data['shift_name'], data['shift_start'], data['shift_end'],
             int(data.get('grace_minutes', 10)), 1 if data.get('active', True) else 0, shift_id)
        )

# ──────────────────────────────────────────────────────────────────────────────
# Rosters
# ──────────────────────────────────────────────────────────────────────────────

def get_roster_for_date(employee_id: int, roster_date: str):
    with db() as conn:
        return conn.execute(
            '''SELECT r.*, s.shift_name, s.shift_start, s.shift_end, s.grace_minutes
               FROM rosters r JOIN shifts s ON s.id = r.shift_id
               WHERE r.employee_id = ? AND r.roster_date = ?''',
            (employee_id, roster_date)
        ).fetchone()

def get_rosters(date_from: str = None, date_to: str = None, employee_id: int = None):
    with db() as conn:
        q = '''SELECT r.*, e.full_name, e.employee_code, s.shift_name, s.shift_start, s.shift_end, s.grace_minutes
               FROM rosters r
               JOIN employees e ON e.id = r.employee_id
               JOIN shifts s ON s.id = r.shift_id
               WHERE 1=1'''
        params = []
        if date_from:
            q += ' AND r.roster_date >= ?'; params.append(date_from)
        if date_to:
            q += ' AND r.roster_date <= ?'; params.append(date_to)
        if employee_id:
            q += ' AND r.employee_id = ?'; params.append(employee_id)
        q += ' ORDER BY r.roster_date, e.full_name'
        return conn.execute(q, params).fetchall()

def upsert_roster(employee_id: int, shift_id: int | None, roster_date: str,
                  is_holiday: bool, notes: str, created_by: int) -> int:
    with db() as conn:
        cur = conn.execute(
            '''INSERT INTO rosters (employee_id, shift_id, roster_date, is_holiday, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(employee_id, roster_date)
               DO UPDATE SET shift_id=excluded.shift_id,
                             is_holiday=excluded.is_holiday,
                             notes=excluded.notes''',
            (employee_id, shift_id, roster_date, 1 if is_holiday else 0, notes, created_by)
        )
        return cur.lastrowid

def save_roster_batch(employee_id: int, entries: list[dict], notes: str, created_by: int):
    """
    entries: list of {roster_date, shift_id|None, is_holiday}
    Saves all rows for the employee in one transaction.
    """
    with db() as conn:
        for entry in entries:
            conn.execute(
                '''INSERT INTO rosters (employee_id, shift_id, roster_date, is_holiday, notes, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(employee_id, roster_date)
                   DO UPDATE SET shift_id=excluded.shift_id,
                                 is_holiday=excluded.is_holiday,
                                 notes=excluded.notes''',
                (employee_id, entry.get('shift_id'), entry['roster_date'],
                 1 if entry.get('is_holiday') else 0, notes, created_by)
            )

def delete_roster(roster_id: int):
    with db() as conn:
        conn.execute('DELETE FROM rosters WHERE id = ?', (roster_id,))

# ──────────────────────────────────────────────────────────────────────────────
# Attendance
# ──────────────────────────────────────────────────────────────────────────────

def get_last_punch(employee_id: int, date_str: str):
    with db() as conn:
        return conn.execute(
            '''SELECT * FROM attendance_logs
               WHERE employee_id = ? AND date(punch_time) = ?
               ORDER BY punch_time DESC LIMIT 1''',
            (employee_id, date_str)
        ).fetchone()

def record_punch(employee_id: int, punch_time: str, punch_type: str,
                 punch_source: str, minutes_late: int, roster_id: int = None,
                 override_reason: str = None, override_by: int = None) -> int:
    with db() as conn:
        cur = conn.execute(
            '''INSERT INTO attendance_logs
               (employee_id, punch_time, punch_type, punch_source, minutes_late,
                roster_id, override_reason, override_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (employee_id, punch_time, punch_type, punch_source, minutes_late,
             roster_id, override_reason, override_by)
        )
        return cur.lastrowid

def get_attendance_logs(date_from: str = None, date_to: str = None,
                        employee_id: int = None, synced: int = None):
    with db() as conn:
        q = '''SELECT al.*, e.full_name, e.employee_code
               FROM attendance_logs al
               JOIN employees e ON e.id = al.employee_id
               WHERE 1=1'''
        params = []
        if date_from:
            q += ' AND date(al.punch_time) >= ?'; params.append(date_from)
        if date_to:
            q += ' AND date(al.punch_time) <= ?'; params.append(date_to)
        if employee_id:
            q += ' AND al.employee_id = ?'; params.append(employee_id)
        if synced is not None:
            q += ' AND al.synced = ?'; params.append(synced)
        q += ' ORDER BY al.punch_time DESC'
        return conn.execute(q, params).fetchall()

def get_unsynced_logs():
    with db() as conn:
        return conn.execute(
            '''SELECT al.*,
                      e.full_name, e.employee_code, e.department,
                      e.designation, e.late_deduction_per_minute
               FROM attendance_logs al
               JOIN employees e ON e.id = al.employee_id
               WHERE al.synced = 0
               ORDER BY al.punch_time
               LIMIT ?''',
            (Config.SYNC_BATCH_SIZE,)
        ).fetchall()

def edit_punch(log_id: int, new_punch_time: str, edited_by: int):
    """Super admin only — update punch time and recalculate minutes_late."""
    with db() as conn:
        conn.execute(
            '''UPDATE attendance_logs
               SET punch_time=?, override_by=?,
                   override_reason=COALESCE(override_reason||' [edited]','[edited by admin]'),
                   synced=0
               WHERE id=?''',
            (new_punch_time, edited_by, log_id)
        )

def get_punch(log_id: int):
    with db() as conn:
        return conn.execute(
            '''SELECT al.*, e.full_name, e.employee_code
               FROM attendance_logs al JOIN employees e ON e.id=al.employee_id
               WHERE al.id=?''', (log_id,)
        ).fetchone()

def mark_synced(log_ids: list):
    with db() as conn:
        placeholders = ','.join('?' * len(log_ids))
        conn.execute(
            f"UPDATE attendance_logs SET synced=1, synced_at=datetime('now') WHERE id IN ({placeholders})",
            log_ids
        )

def record_sync_log(records_sent: int, status: str, error_message: str,
                    synced_by: int, sync_detail: str = None):
    with db() as conn:
        conn.execute(
            'INSERT INTO sync_log (records_sent, status, error_message, synced_by, sync_detail) '
            'VALUES (?, ?, ?, ?, ?)',
            (records_sent, status, error_message, synced_by, sync_detail)
        )

def get_sync_history(limit=20):
    with db() as conn:
        return conn.execute(
            '''SELECT sl.*, u.username FROM sync_log sl
               LEFT JOIN app_users u ON u.id = sl.synced_by
               ORDER BY sl.synced_at DESC LIMIT ?''',
            (limit,)
        ).fetchall()

# ──────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ──────────────────────────────────────────────────────────────────────────────

def get_today_stats(date_str: str) -> dict:
    with db() as conn:
        total_employees = conn.execute(
            'SELECT COUNT(*) FROM employees WHERE active = 1'
        ).fetchone()[0]

        present = conn.execute(
            '''SELECT COUNT(DISTINCT employee_id) FROM attendance_logs
               WHERE date(punch_time) = ? AND punch_type = 'in' ''',
            (date_str,)
        ).fetchone()[0]

        late = conn.execute(
            '''SELECT COUNT(DISTINCT employee_id) FROM attendance_logs
               WHERE date(punch_time) = ? AND punch_type = 'in' AND minutes_late > 0''',
            (date_str,)
        ).fetchone()[0]

        unsynced = conn.execute(
            'SELECT COUNT(*) FROM attendance_logs WHERE synced = 0'
        ).fetchone()[0]

        return {
            'total_employees': total_employees,
            'present': present,
            'absent': total_employees - present,
            'late': late,
            'unsynced': unsynced,
        }

# ──────────────────────────────────────────────────────────────────────────────
# App users management
# ──────────────────────────────────────────────────────────────────────────────

def get_app_users():
    with db() as conn:
        return conn.execute('SELECT id, username, full_name, role, active, created_at, last_login FROM app_users').fetchall()

def create_app_user(username: str, password: str, full_name: str, role: str) -> int:
    with db() as conn:
        cur = conn.execute(
            'INSERT INTO app_users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
            (username, hash_password(password), full_name, role)
        )
        return cur.lastrowid

def update_app_user_password(user_id: int, new_password: str):
    with db() as conn:
        conn.execute(
            'UPDATE app_users SET password_hash = ? WHERE id = ?',
            (hash_password(new_password), user_id)
        )

def toggle_app_user(user_id: int, active: bool):
    with db() as conn:
        conn.execute('UPDATE app_users SET active = ? WHERE id = ?', (1 if active else 0, user_id))

# ──────────────────────────────────────────────────────────────────────────────
# App settings (key-value store)
# ──────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    with db() as conn:
        row = conn.execute('SELECT value FROM app_settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else default

def set_setting(key: str, value: str):
    with db() as conn:
        conn.execute(
            'INSERT INTO app_settings (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            (key, value)
        )

# ──────────────────────────────────────────────────────────────────────────────
# Sync settings — stored in app_settings; API key is XOR-encrypted at rest
# ──────────────────────────────────────────────────────────────────────────────

def _enc_key() -> bytes:
    return hashlib.sha256(Config.SECRET_KEY.encode('utf-8')).digest()

def encrypt_setting(plaintext: str) -> str:
    """XOR-encrypt a string with the app SECRET_KEY; returns base64 url-safe string."""
    if not plaintext:
        return ''
    key  = _enc_key()
    data = plaintext.encode('utf-8')
    enc  = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    return base64.urlsafe_b64encode(enc).decode('ascii')

def decrypt_setting(ciphertext: str) -> str:
    """Reverse of encrypt_setting."""
    if not ciphertext:
        return ''
    key  = _enc_key()
    data = base64.urlsafe_b64decode(ciphertext.encode('ascii'))
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data)).decode('utf-8')

# Settings keys used for Supabase sync
_SB_URL_KEY   = 'supabase_url'
_SB_KEY_ENC   = 'supabase_key_enc'   # service role key, encrypted
_SB_TABLE_KEY = 'supabase_table'

def get_sync_settings() -> dict:
    """
    Return Supabase sync config.  DB values take precedence over env vars.
    api_key is returned DECRYPTED (ready to use in HTTP headers).
    """
    url     = get_setting(_SB_URL_KEY)   or Config.SUPABASE_URL
    key_enc = get_setting(_SB_KEY_ENC)
    api_key = decrypt_setting(key_enc) if key_enc else Config.SUPABASE_KEY
    table   = get_setting(_SB_TABLE_KEY) or Config.SUPABASE_TABLE
    return {'url': url, 'api_key': api_key, 'table': table}

def save_sync_settings(url: str, api_key: str, table: str):
    """Persist Supabase sync config. api_key is stored encrypted."""
    set_setting(_SB_URL_KEY,   url.strip())
    set_setting(_SB_KEY_ENC,   encrypt_setting(api_key.strip()))
    set_setting(_SB_TABLE_KEY, table.strip())

def get_sync_settings_display() -> dict:
    """
    Like get_sync_settings but returns the RAW (encrypted) api_key for display.
    Caller decrypts only after the user has been password-verified.
    """
    url     = get_setting(_SB_URL_KEY)   or Config.SUPABASE_URL
    key_enc = get_setting(_SB_KEY_ENC)   or ''
    table   = get_setting(_SB_TABLE_KEY) or Config.SUPABASE_TABLE
    return {'url': url, 'api_key_enc': key_enc, 'table': table}

# ──────────────────────────────────────────────────────────────────────────────
# Manual mode helpers
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
# Face templates
# ──────────────────────────────────────────────────────────────────────────────

def save_face_template(employee_id: int, embedding_json: str, quality: float, enrolled_by: int):
    with db() as conn:
        conn.execute(
            '''INSERT INTO face_templates (employee_id, embedding, quality, enrolled_by)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(employee_id)
               DO UPDATE SET embedding=excluded.embedding,
                             quality=excluded.quality,
                             enrolled_at=datetime('now'),
                             enrolled_by=excluded.enrolled_by''',
            (employee_id, embedding_json, quality, enrolled_by)
        )

def get_face_template(employee_id: int):
    with db() as conn:
        return conn.execute(
            'SELECT * FROM face_templates WHERE employee_id = ?', (employee_id,)
        ).fetchone()

def get_all_face_templates():
    """Load all face templates for 1:N identification."""
    with db() as conn:
        return conn.execute(
            '''SELECT ft.employee_id, ft.embedding, ft.quality,
                      e.full_name, e.employee_code
               FROM face_templates ft
               JOIN employees e ON e.id = ft.employee_id
               WHERE e.active = 1'''
        ).fetchall()

def delete_face_template(employee_id: int):
    with db() as conn:
        conn.execute('DELETE FROM face_templates WHERE employee_id = ?', (employee_id,))

# ──────────────────────────────────────────────────────────────────────────────
# Payroll queries
# ──────────────────────────────────────────────────────────────────────────────

def get_payroll_detail(employee_id: int, date_from: str, date_to: str) -> dict:
    """
    Returns employee info + day-by-day payroll records for the period.
    Only days with a roster entry are included (rosters define the schedule).
    """
    with db() as conn:
        employee = conn.execute(
            'SELECT * FROM employees WHERE id = ?', (employee_id,)
        ).fetchone()
        if not employee:
            return {}

        rosters = conn.execute(
            '''SELECT r.*, s.shift_name, s.shift_start, s.shift_end, s.grace_minutes
               FROM rosters r
               LEFT JOIN shifts s ON s.id = r.shift_id
               WHERE r.employee_id = ? AND r.roster_date BETWEEN ? AND ?
               ORDER BY r.roster_date''',
            (employee_id, date_from, date_to)
        ).fetchall()

        logs = conn.execute(
            '''SELECT * FROM attendance_logs
               WHERE employee_id = ? AND date(punch_time) BETWEEN ? AND ?
               ORDER BY punch_time''',
            (employee_id, date_from, date_to)
        ).fetchall()

    # Index logs by date
    from collections import defaultdict
    logs_by_date = defaultdict(list)
    for log in logs:
        logs_by_date[log['punch_time'][:10]].append(dict(log))

    rate = float(employee['late_deduction_per_minute'] or 0)
    daily_records = []

    for roster in rosters:
        date_str  = roster['roster_date']
        is_holiday = bool(roster['is_holiday'])
        day_logs  = logs_by_date.get(date_str, [])
        punch_ins  = [l for l in day_logs if l['punch_type'] == 'in']
        punch_outs = [l for l in day_logs if l['punch_type'] == 'out']
        first_in   = punch_ins[0]  if punch_ins  else None
        last_out   = punch_outs[-1] if punch_outs else None

        if is_holiday:
            status = 'Holiday'
        elif first_in:
            status = 'Present'
        else:
            status = 'Absent'

        minutes_late = first_in['minutes_late'] if first_in else 0
        daily_deduction = round(minutes_late * rate, 2)

        hours_worked = None
        if first_in and last_out:
            from datetime import datetime
            t_in  = datetime.strptime(first_in['punch_time'],  '%Y-%m-%d %H:%M:%S')
            t_out = datetime.strptime(last_out['punch_time'],  '%Y-%m-%d %H:%M:%S')
            hours_worked = round((t_out - t_in).total_seconds() / 3600, 2)

        daily_records.append({
            'date':            date_str,
            'shift_name':      roster['shift_name'],
            'shift_start':     roster['shift_start'],
            'is_holiday':      is_holiday,
            'status':          status,
            'punch_in':        first_in['punch_time'][11:16]  if first_in  else None,
            'punch_out':       last_out['punch_time'][11:16]  if last_out  else None,
            'hours_worked':    hours_worked,
            'minutes_late':    minutes_late,
            'daily_deduction': daily_deduction,
            'punch_source':    first_in['punch_source'] if first_in else None,
        })

    # Totals
    working_days  = sum(1 for r in daily_records if not r['is_holiday'])
    present       = sum(1 for r in daily_records if r['status'] == 'Present')
    absent        = sum(1 for r in daily_records if r['status'] == 'Absent')
    holidays      = sum(1 for r in daily_records if r['status'] == 'Holiday')
    late_days     = sum(1 for r in daily_records if r['minutes_late'] > 0)
    total_late    = sum(r['minutes_late'] for r in daily_records)
    total_deduction = round(sum(r['daily_deduction'] for r in daily_records), 2)

    return {
        'employee':        dict(employee),
        'date_from':       date_from,
        'date_to':         date_to,
        'daily_records':   daily_records,
        'working_days':    working_days,
        'present':         present,
        'absent':          absent,
        'holidays':        holidays,
        'late_days':       late_days,
        'total_late_mins': total_late,
        'total_deduction': total_deduction,
        'deduction_rate':  rate,
    }


def get_payroll_overview(date_from: str, date_to: str) -> list[dict]:
    """Summary row per active employee for the payroll period."""
    employees = get_employees(active_only=True)
    overview = []
    for emp in employees:
        detail = get_payroll_detail(emp['id'], date_from, date_to)
        if not detail or not detail.get('daily_records'):
            # Include employees with no roster so admin can see gaps
            overview.append({
                'employee_id':   emp['id'],
                'employee_code': emp['employee_code'],
                'full_name':     emp['full_name'],
                'department':    emp['department'],
                'working_days':  0,
                'present':       0,
                'absent':        0,
                'holidays':      0,
                'late_days':     0,
                'total_late_mins': 0,
                'total_deduction': 0,
                'deduction_rate':  float(emp['late_deduction_per_minute'] or 0),
                'no_roster':     True,
            })
        else:
            overview.append({
                'employee_id':     emp['id'],
                'employee_code':   emp['employee_code'],
                'full_name':       emp['full_name'],
                'department':      emp['department'] or '',
                'monthly_salary':  float(emp['monthly_salary'] or 0),
                'weekly_off_day':  int(emp['weekly_off_day'] or 6),
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

MANUAL_MODE_KEY = 'manual_mode_date'

def get_manual_mode_date() -> str | None:
    """Returns the date string if manual mode is active, else None."""
    return get_setting(MANUAL_MODE_KEY)

def enable_manual_mode(date_str: str):
    set_setting(MANUAL_MODE_KEY, date_str)

def disable_manual_mode():
    set_setting(MANUAL_MODE_KEY, '')
