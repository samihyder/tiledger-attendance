-- TiLedger Attendance System — Supabase Schema
-- Run this once in your Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- Supabase project: https://app.supabase.com

-- App users (login accounts)
CREATE TABLE IF NOT EXISTS app_users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('super_admin', 'manager', 'system_admin', 'store')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    last_login    TEXT
);

-- Employees
CREATE TABLE IF NOT EXISTS employees (
    id                       BIGSERIAL PRIMARY KEY,
    employee_code            TEXT UNIQUE NOT NULL,
    full_name                TEXT NOT NULL,
    department               TEXT,
    designation              TEXT,
    phone                    TEXT,
    email                    TEXT,
    joining_date             TEXT,
    active                   INTEGER NOT NULL DEFAULT 1,
    created_at               TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    created_by               INTEGER REFERENCES app_users(id),
    late_deduction_per_minute REAL NOT NULL DEFAULT 0,
    monthly_salary           REAL NOT NULL DEFAULT 0,
    weekly_off_day           INTEGER NOT NULL DEFAULT 6,
    deduction_rate_override  INTEGER NOT NULL DEFAULT 0
);

-- Shifts
CREATE TABLE IF NOT EXISTS shifts (
    id            BIGSERIAL PRIMARY KEY,
    shift_name    TEXT NOT NULL,
    shift_start   TEXT NOT NULL,
    shift_end     TEXT NOT NULL,
    grace_minutes INTEGER NOT NULL DEFAULT 10
);

-- Rosters
CREATE TABLE IF NOT EXISTS rosters (
    id           BIGSERIAL PRIMARY KEY,
    employee_id  INTEGER NOT NULL REFERENCES employees(id),
    shift_id     INTEGER NOT NULL REFERENCES shifts(id),
    roster_date  TEXT NOT NULL,
    is_holiday   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(employee_id, roster_date)
);

-- Biometric templates
CREATE TABLE IF NOT EXISTS biometric_templates (
    id            BIGSERIAL PRIMARY KEY,
    employee_id   INTEGER NOT NULL REFERENCES employees(id),
    finger_index  INTEGER NOT NULL,
    template_data BYTEA NOT NULL,
    enrolled_at   TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    UNIQUE(employee_id, finger_index)
);

-- Face templates
CREATE TABLE IF NOT EXISTS face_templates (
    id          BIGSERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    embedding   TEXT NOT NULL,
    enrolled_at TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    UNIQUE(employee_id)
);

-- Attendance logs (individual punches from punch stations)
CREATE TABLE IF NOT EXISTS attendance_logs (
    id              BIGSERIAL PRIMARY KEY,
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
    created_at      TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE INDEX IF NOT EXISTS idx_attendance_employee_date
    ON attendance_logs(employee_id, punch_time);
CREATE INDEX IF NOT EXISTS idx_attendance_synced
    ON attendance_logs(synced) WHERE synced = 0;

-- Sync log
CREATE TABLE IF NOT EXISTS sync_log (
    id             BIGSERIAL PRIMARY KEY,
    synced_at      TEXT NOT NULL DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    records_sent   INTEGER NOT NULL DEFAULT 0,
    status         TEXT NOT NULL CHECK(status IN ('success', 'failed', 'partial')),
    error_message  TEXT,
    synced_by      INTEGER REFERENCES app_users(id),
    sync_detail    TEXT
);

-- App settings (key-value store)
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Default shift (9 AM – 6 PM, 10 min grace)
INSERT INTO shifts (shift_name, shift_start, shift_end, grace_minutes)
VALUES ('Morning Shift', '09:00', '18:00', 10)
ON CONFLICT DO NOTHING;

-- Default super admin (change password after first login!)
-- Default password: admin@2026
INSERT INTO app_users (username, password_hash, full_name, role)
VALUES (
    'admin',
    '8b3ce0c3977ee6e8d53efeb1fb5b4f82bfb85e44b706c4eded197bd78875da67',  -- SHA-256 of 'admin@2026'
    'Super Admin',
    'super_admin'
)
ON CONFLICT (username) DO NOTHING;
