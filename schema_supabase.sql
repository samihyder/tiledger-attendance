-- TiLedger Attendance System — Supabase Schema
-- Run in: Supabase Dashboard → SQL Editor → New query
--
-- Uses the default `public` schema — no extra Supabase config needed.
-- Safe to re-run: all DROPs are CASCADE so a fresh run wipes and rebuilds.

-- ── Drop in reverse FK order ──────────────────────────────────────────────────
DROP TABLE IF EXISTS public.overtime_requests   CASCADE;
DROP TABLE IF EXISTS public.leave_requests      CASCADE;
DROP TABLE IF EXISTS public.payroll_adjustments CASCADE;
DROP TABLE IF EXISTS public.sync_log            CASCADE;
DROP TABLE IF EXISTS public.face_templates      CASCADE;
DROP TABLE IF EXISTS public.biometric_templates CASCADE;
DROP TABLE IF EXISTS public.attendance_logs     CASCADE;
DROP TABLE IF EXISTS public.rosters             CASCADE;
DROP TABLE IF EXISTS public.shifts              CASCADE;
DROP TABLE IF EXISTS public.employees           CASCADE;
DROP TABLE IF EXISTS public.app_settings        CASCADE;
DROP TABLE IF EXISTS public.app_users           CASCADE;

-- ── App users ─────────────────────────────────────────────────────────────────
CREATE TABLE public.app_users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('super_admin','manager','system_admin','store','cashier')),
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

-- ── Employees ─────────────────────────────────────────────────────────────────
CREATE TABLE public.employees (
    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_code             TEXT UNIQUE NOT NULL,
    full_name                 TEXT NOT NULL,
    department                TEXT,
    designation               TEXT,
    phone                     TEXT,
    email                     TEXT,
    joining_date              TEXT,
    active                    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by                BIGINT REFERENCES public.app_users(id),
    late_deduction_per_minute REAL NOT NULL DEFAULT 0,
    monthly_salary            REAL NOT NULL DEFAULT 0,
    weekly_off_day            INTEGER NOT NULL DEFAULT 6,
    deduction_rate_override   BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── Shifts ────────────────────────────────────────────────────────────────────
CREATE TABLE public.shifts (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shift_name    TEXT NOT NULL,
    shift_start   TEXT NOT NULL,
    shift_end     TEXT NOT NULL,
    grace_minutes INTEGER NOT NULL DEFAULT 10,
    active        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ── Rosters ───────────────────────────────────────────────────────────────────
CREATE TABLE public.rosters (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id),
    shift_id    BIGINT REFERENCES public.shifts(id),
    roster_date TEXT NOT NULL,
    is_holiday  BOOLEAN NOT NULL DEFAULT FALSE,
    notes       TEXT,
    created_by  BIGINT REFERENCES public.app_users(id),
    UNIQUE(employee_id, roster_date)
);

CREATE INDEX idx_roster_date_emp ON public.rosters(roster_date, employee_id);
CREATE INDEX idx_roster_shift    ON public.rosters(shift_id);

-- ── Biometric templates ───────────────────────────────────────────────────────
CREATE TABLE public.biometric_templates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id   BIGINT NOT NULL REFERENCES public.employees(id),
    finger_index  INTEGER NOT NULL,
    template_data BYTEA NOT NULL,
    enrolled_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(employee_id, finger_index)
);

-- ── Face templates ────────────────────────────────────────────────────────────
CREATE TABLE public.face_templates (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id),
    embedding   TEXT NOT NULL,
    quality     REAL NOT NULL DEFAULT 0,
    enrolled_by BIGINT REFERENCES public.app_users(id),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(employee_id)
);

-- ── Attendance logs ───────────────────────────────────────────────────────────
CREATE TABLE public.attendance_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id     BIGINT NOT NULL REFERENCES public.employees(id),
    punch_time      TIMESTAMPTZ NOT NULL,
    punch_type      TEXT NOT NULL CHECK(punch_type IN ('in','out')),
    punch_source    TEXT NOT NULL DEFAULT 'manual'
                        CHECK(punch_source IN ('biometric','manual','face')),
    minutes_late    INTEGER NOT NULL DEFAULT 0,
    overtime_minutes INTEGER NOT NULL DEFAULT 0,
    roster_id       BIGINT REFERENCES public.rosters(id),
    override_reason TEXT,
    override_by     BIGINT REFERENCES public.app_users(id),
    synced          BOOLEAN NOT NULL DEFAULT FALSE,
    synced_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_att_employee_date ON public.attendance_logs(employee_id, punch_time);
CREATE INDEX idx_att_synced        ON public.attendance_logs(synced) WHERE synced = FALSE;

-- ── Overtime requests ─────────────────────────────────────────────────────────
CREATE TABLE public.overtime_requests (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id      BIGINT NOT NULL REFERENCES public.employees(id),
    attendance_log_id BIGINT REFERENCES public.attendance_logs(id),
    ot_date          TEXT NOT NULL,
    shift_end_time   TEXT NOT NULL,
    actual_out_time  TEXT NOT NULL,
    ot_minutes       INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK(status IN ('pending','approved','rejected')),
    approved_by      BIGINT REFERENCES public.app_users(id),
    approved_at      TIMESTAMPTZ,
    reject_reason    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ot_employee ON public.overtime_requests(employee_id);
CREATE INDEX idx_ot_status   ON public.overtime_requests(status) WHERE status = 'pending';

-- ── Leave requests ────────────────────────────────────────────────────────────
CREATE TABLE public.leave_requests (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id),
    leave_type  TEXT NOT NULL CHECK(leave_type IN
                ('annual','sick','unpaid','emergency','other')),
    date_from   TEXT NOT NULL,
    date_to     TEXT NOT NULL,
    days        INTEGER NOT NULL DEFAULT 1,
    reason      TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected')),
    approved_by BIGINT REFERENCES public.app_users(id),
    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leave_employee ON public.leave_requests(employee_id);
CREATE INDEX idx_leave_dates    ON public.leave_requests(date_from, date_to);

-- ── Sync log ──────────────────────────────────────────────────────────────────
CREATE TABLE public.sync_log (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    records_sent  INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL CHECK(status IN ('success','failed','partial')),
    error_message TEXT,
    synced_by     BIGINT REFERENCES public.app_users(id),
    sync_detail   TEXT
);

-- ── Payroll adjustments ───────────────────────────────────────────────────────
CREATE TABLE public.payroll_adjustments (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES public.employees(id),
    period_from TEXT NOT NULL,
    period_to   TEXT NOT NULL,
    adj_type    TEXT NOT NULL CHECK(adj_type IN
                ('bonus','advance_payment','loan_recovery','deduction','correction','other')),
    amount      REAL NOT NULL CHECK(amount > 0),
    description TEXT NOT NULL,
    created_by  BIGINT NOT NULL REFERENCES public.app_users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_adj_employee ON public.payroll_adjustments(employee_id);
CREATE INDEX idx_adj_period   ON public.payroll_adjustments(period_from, period_to);

-- ── App settings ──────────────────────────────────────────────────────────────
CREATE TABLE public.app_settings (
    id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key   TEXT UNIQUE NOT NULL,
    value TEXT
);

-- ── Seed defaults ─────────────────────────────────────────────────────────────
INSERT INTO public.shifts (shift_name, shift_start, shift_end, grace_minutes)
VALUES ('Morning Shift', '09:00:00', '18:00:00', 10);

-- OT settings
INSERT INTO public.app_settings (key, value) VALUES
    ('ot_threshold_minutes', '30'),
    ('ot_pay_multiplier',    '1.5');

-- Default super admin  (password: admin@2026 — change immediately after login)
INSERT INTO public.app_users (username, password_hash, full_name, role)
VALUES (
    'admin',
    '8b3ce0c3977ee6e8d53efeb1fb5b4f82bfb85e44b706c4eded197bd78875da67',
    'Super Admin',
    'super_admin'
);
