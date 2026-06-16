-- TiLedger v2 Migration — run in Supabase SQL Editor
-- Adds: overtime_minutes column, overtime_requests, leave_requests, payroll_adjustments tables
-- Safe to re-run: uses IF NOT EXISTS / IF NOT EXISTS guards

-- ── attendance_logs: add overtime_minutes ─────────────────────────────────────
ALTER TABLE public.attendance_logs
  ADD COLUMN IF NOT EXISTS overtime_minutes INTEGER NOT NULL DEFAULT 0;

-- ── payroll_adjustments ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payroll_adjustments (
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

CREATE INDEX IF NOT EXISTS idx_adj_employee ON public.payroll_adjustments(employee_id);
CREATE INDEX IF NOT EXISTS idx_adj_period   ON public.payroll_adjustments(period_from, period_to);

-- ── overtime_requests ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.overtime_requests (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id       BIGINT NOT NULL REFERENCES public.employees(id),
    attendance_log_id BIGINT REFERENCES public.attendance_logs(id),
    ot_date           TEXT NOT NULL,
    shift_end_time    TEXT NOT NULL,
    actual_out_time   TEXT NOT NULL,
    ot_minutes        INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK(status IN ('pending','approved','rejected')),
    approved_by       BIGINT REFERENCES public.app_users(id),
    approved_at       TIMESTAMPTZ,
    reject_reason     TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ot_employee ON public.overtime_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_ot_status   ON public.overtime_requests(status) WHERE status = 'pending';

-- ── leave_requests ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.leave_requests (
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

CREATE INDEX IF NOT EXISTS idx_leave_employee ON public.leave_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_dates    ON public.leave_requests(date_from, date_to);

-- ── OT settings (insert if not present) ──────────────────────────────────────
INSERT INTO public.app_settings (key, value) VALUES ('ot_threshold_minutes', '30')
    ON CONFLICT (key) DO NOTHING;
INSERT INTO public.app_settings (key, value) VALUES ('ot_pay_multiplier', '1.5')
    ON CONFLICT (key) DO NOTHING;
