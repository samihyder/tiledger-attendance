-- TiLedger Attendance System — Supabase Schema
-- Run this in Supabase Dashboard → SQL Editor → New query
--
-- If you ran a previous version and got errors, the DROP lines below
-- clean up the broken state first (safe to run on a fresh project).

-- ── Drop in reverse FK order ──────────────────────────────────────────────────
DROP TABLE IF EXISTS sync_log          CASCADE;
DROP TABLE IF EXISTS face_templates    CASCADE;
DROP TABLE IF EXISTS biometric_templates CASCADE;
DROP TABLE IF EXISTS attendance_logs   CASCADE;
DROP TABLE IF EXISTS rosters           CASCADE;
DROP TABLE IF EXISTS shifts            CASCADE;
DROP TABLE IF EXISTS employees         CASCADE;
DROP TABLE IF EXISTS app_settings      CASCADE;
DROP TABLE IF EXISTS app_users         CASCADE;

-- ── App users ─────────────────────────────────────────────────────────────────
CREATE TABLE app_users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('super_admin','manager','system_admin','store')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
    last_login    TEXT
);

-- ── Employees ─────────────────────────────────────────────────────────────────
CREATE TABLE employees (
    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_code             TEXT UNIQUE NOT NULL,
    full_name                 TEXT NOT NULL,
    department                TEXT,
    designation               TEXT,
    phone                     TEXT,
    email                     TEXT,
    joining_date              TEXT,
    active                    INTEGER NOT NULL DEFAULT 1,
    created_at                TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
    created_by                BIGINT REFERENCES app_users(id),
    late_deduction_per_minute REAL NOT NULL DEFAULT 0,
    monthly_salary            REAL NOT NULL DEFAULT 0,
    weekly_off_day            INTEGER NOT NULL DEFAULT 6,
    deduction_rate_override   INTEGER NOT NULL DEFAULT 0
);

-- ── Shifts ────────────────────────────────────────────────────────────────────
CREATE TABLE shifts (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shift_name    TEXT NOT NULL,
    shift_start   TEXT NOT NULL,
    shift_end     TEXT NOT NULL,
    grace_minutes INTEGER NOT NULL DEFAULT 10
);

-- ── Rosters ───────────────────────────────────────────────────────────────────
CREATE TABLE rosters (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employees(id),
    shift_id    BIGINT NOT NULL REFERENCES shifts(id),
    roster_date TEXT NOT NULL,
    is_holiday  INTEGER NOT NULL DEFAULT 0,
    UNIQUE(employee_id, roster_date)
);

-- ── Biometric templates ───────────────────────────────────────────────────────
CREATE TABLE biometric_templates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id   BIGINT NOT NULL REFERENCES employees(id),
    finger_index  INTEGER NOT NULL,
    template_data BYTEA NOT NULL,
    enrolled_at   TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
    UNIQUE(employee_id, finger_index)
);

-- ── Face templates ────────────────────────────────────────────────────────────
CREATE TABLE face_templates (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employees(id),
    embedding   TEXT NOT NULL,
    enrolled_at TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
    UNIQUE(employee_id)
);

-- ── Attendance logs ───────────────────────────────────────────────────────────
CREATE TABLE attendance_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id     BIGINT NOT NULL REFERENCES employees(id),
    punch_time      TEXT NOT NULL,
    punch_type      TEXT NOT NULL CHECK(punch_type IN ('in','out')),
    punch_source    TEXT NOT NULL DEFAULT 'biometric'
                        CHECK(punch_source IN ('biometric','manual')),
    minutes_late    INTEGER NOT NULL DEFAULT 0,
    roster_id       BIGINT REFERENCES rosters(id),
    override_reason TEXT,
    override_by     BIGINT REFERENCES app_users(id),
    synced          INTEGER NOT NULL DEFAULT 0,
    synced_at       TEXT,
    created_at      TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS')
);

CREATE INDEX idx_attendance_employee_date ON attendance_logs(employee_id, punch_time);
CREATE INDEX idx_attendance_synced        ON attendance_logs(synced) WHERE synced = 0;

-- ── Sync log ──────────────────────────────────────────────────────────────────
CREATE TABLE sync_log (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at    TEXT NOT NULL DEFAULT TO_CHAR(NOW(),'YYYY-MM-DD HH24:MI:SS'),
    records_sent INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL CHECK(status IN ('success','failed','partial')),
    error_message TEXT,
    synced_by    BIGINT REFERENCES app_users(id),
    sync_detail  TEXT
);

-- ── App settings (key-value, no auto-id needed but kept consistent) ───────────
CREATE TABLE app_settings (
    id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key   TEXT UNIQUE NOT NULL,
    value TEXT
);

-- ── Seed data ─────────────────────────────────────────────────────────────────
INSERT INTO shifts (shift_name, shift_start, shift_end, grace_minutes)
VALUES ('Morning Shift', '09:00', '18:00', 10);

-- Default super admin — password: admin@2026  (change immediately after first login)
INSERT INTO app_users (username, password_hash, full_name, role)
VALUES (
    'admin',
    '8b3ce0c3977ee6e8d53efeb1fb5b4f82bfb85e44b706c4eded197bd78875da67',
    'Super Admin',
    'super_admin'
);
