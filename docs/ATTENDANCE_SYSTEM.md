# TiLedger Attendance System — Technical Document

## Overview

A secure, local desktop-based Employee Attendance and Roster Management System built with Python (Flask) and SQLite. Runs entirely on `localhost` — no internet required for daily operation. Syncs attendance data to the Supabase/ERP system on demand.

---

## Architecture

```
attendanceappv1/
├── app.py                      # Flask app factory, startup
├── config.py                   # All configuration (env-var driven)
├── db_manager.py               # All SQLite operations (single source of truth)
├── attendance_logic.py         # Late calculation, punch processing
├── biometric_service.py        # ZKTeco SDK wrapper + Mock device
├── sync_service.py             # Supabase sync (HTTP push)
├── auth.py                     # RBAC decorators and session helpers
├── routes/
│   ├── __init__.py             # Blueprint registration
│   ├── auth_routes.py          # Login, logout, override verify
│   ├── main_routes.py          # Dashboard
│   ├── employee_routes.py      # Employee CRUD + biometric enrollment
│   ├── roster_routes.py        # Shift + roster CRUD
│   ├── attendance_routes.py    # Punch screen, log, manual entry
│   └── sync_routes.py          # ERP sync trigger
├── templates/                  # Jinja2 HTML templates (Bootstrap 5)
├── static/                     # CSS, JS
├── instance/
│   └── attendance.db           # SQLite database (auto-created)
└── docs/
    └── ATTENDANCE_SYSTEM.md    # This document
```

---

## Database Schema

### `app_users`
Login accounts for the attendance system itself.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| username | TEXT UNIQUE | login username |
| password_hash | TEXT | SHA-256 hash |
| full_name | TEXT | display name |
| role | TEXT | `super_admin` / `manager` / `system_admin` |
| active | INTEGER | 1=active, 0=disabled |
| last_login | TEXT | ISO datetime |

### `employees`
Staff who use the biometric punch system.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_code | TEXT UNIQUE | e.g. `EMP-001` |
| full_name | TEXT | |
| department | TEXT | |
| designation | TEXT | |
| phone / email | TEXT | |
| joining_date | TEXT | YYYY-MM-DD |
| active | INTEGER | soft delete |

### `biometric_templates`
Fingerprint minutiae templates from the ZKTeco SDK. **No fingerprint images are stored** — only the mathematical template.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK | → employees |
| finger_index | INTEGER | 0–9 (see finger map) |
| finger_label | TEXT | e.g. "Right Index" |
| template_data | BLOB | minutiae template bytes from SDK |
| quality_score | INTEGER | 0–100 |
| enrolled_by | INTEGER FK | → app_users |

**Finger index map:**
```
0 = Right Thumb     5 = Left Thumb
1 = Right Index ★   6 = Left Index ★★
2 = Right Middle    7 = Left Middle
3 = Right Ring      8 = Left Ring
4 = Right Little    9 = Left Little

★  Primary finger (default enrollment)
★★ Backup finger (required for redundancy)
```

### `shifts`
Reusable shift templates.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| shift_name | TEXT | e.g. "Morning Shift" |
| shift_start | TEXT | HH:MM |
| shift_end | TEXT | HH:MM |
| grace_minutes | INTEGER | default 10 |
| active | INTEGER | |

### `rosters`
Daily assignment of an employee to a shift.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK | |
| shift_id | INTEGER FK | |
| roster_date | TEXT | YYYY-MM-DD |
| UNIQUE | (employee_id, roster_date) | one shift per day per employee |

### `attendance_logs`
Every punch-in and punch-out event.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| employee_id | INTEGER FK | |
| punch_time | TEXT | ISO datetime `YYYY-MM-DD HH:MM:SS` |
| punch_type | TEXT | `in` or `out` |
| punch_source | TEXT | `biometric` or `manual` |
| minutes_late | INTEGER | 0 if on time |
| roster_id | INTEGER FK | roster used for late calculation |
| override_reason | TEXT | mandatory for manual punches |
| override_by | INTEGER FK | → app_users |
| synced | INTEGER | 0=pending, 1=sent to ERP |
| synced_at | TEXT | ISO datetime of sync |

### `sync_log`
History of every sync attempt.

---

## Late-Marking Algorithm

```
def calculate_minutes_late(punch_time, shift_start, grace_minutes):

    grace_end = shift_start + timedelta(minutes=grace_minutes)

    if punch_time <= grace_end:
        return 0                           # on time (within grace window)

    late_seconds = (punch_time - shift_start).total_seconds()
    return int(late_seconds / 60)          # measured from shift_start, not grace_end
```

**Example:**
- Shift starts: 09:00
- Grace period: 10 minutes (grace window ends at 09:10)
- Employee punches in at 09:15

→ `minutes_late = (09:15 − 09:00) = 15 minutes`

The grace period does not reduce the late count — it only determines the threshold.
An employee at 09:05 is **on time** (0 late). An employee at 09:11 is **11 minutes late**.

---

## Role-Based Access Control (RBAC)

| Feature | Super Admin | Manager | System Admin |
|---|:---:|:---:|:---:|
| View dashboard | ✓ | ✓ | ✓ |
| Punch screen | ✓ | ✓ | ✓ |
| View attendance log | ✓ | ✓ | ✓ |
| Export attendance | ✓ | ✓ | ✗ |
| Manual attendance | ✓ + PIN | ✓ + PIN | ✗ |
| Roster CRUD | ✓ | ✓ | ✗ |
| Employee CRUD | ✓ | ✗ | ✓ |
| Biometric enrollment | ✓ | ✗ | ✓ |
| Sync to ERP | ✓ | ✓ | ✗ |
| Manage app users | ✓ | ✗ | ✗ |
| System settings | ✓ | ✗ | ✗ |

### Manual Attendance Override
The "Manual Entry" page requires a secondary override password (separate from the login password) before the entry form becomes active. This prevents casual misuse by managers. The override is session-scoped and automatically clears after one successful submission, requiring re-authentication for each manual punch.

The override password is set via the `OVERRIDE_PASSWORD` environment variable (never in code).

---

## Biometric Integration — ZKTeco ZK9500

### SDK Installation

1. Download the **ZKFinger SDK** from [ZKTeco Developer Zone](https://www.zkteco.com/en/developer).
2. Extract and copy the appropriate binary to the project root:
   - Windows: `zkfp.dll` + `zkfp2.dll`
   - Linux: `libzkfp.so`
3. Set the path via environment variable if not in the project root:
   ```
   ZK_SDK_PATH=/path/to/libzkfp.so
   ```
4. Install any system USB drivers provided by ZKTeco for your OS.

### Mock Mode (development without hardware)
```bash
BIOMETRIC_MOCK=true python app.py
```
All biometric operations are simulated. Templates are fake byte arrays. Use this for UI development and testing.

### Enrollment Protocol
- Register **Right Index** (primary) + **Left Index** (backup) for every employee.
- Each enrollment captures **3 scans** and merges them into a single high-quality template using `ZKFP_DBMerge`.
- Only the **minutiae template** (mathematical map) is stored — never the fingerprint image. This is mandatory for privacy compliance.

### Identification Flow (1:N)
1. All enrolled templates are loaded from SQLite.
2. `ZKFP_DBIdentify` compares the live scan against all templates simultaneously.
3. Match threshold: `score >= 45` (configurable in `config.py`).
4. Matched employee ID → late calculation → attendance record.

---

## Sync to Supabase ERP

### Configuration
Set these environment variables (or use a `.env` file):
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SYNC_ENDPOINT=/api/attendance/sync
```

### How it works
1. Query `attendance_logs WHERE synced = 0` (up to 200 records per batch).
2. POST to `SUPABASE_URL + SUPABASE_SYNC_ENDPOINT` with payload:
   ```json
   {
     "records": [
       {
         "local_id": 42,
         "employee_code": "EMP-001",
         "full_name": "Ali Hassan",
         "punch_time": "2026-05-30 09:05:00",
         "punch_type": "in",
         "punch_source": "biometric",
         "minutes_late": 5,
         "override_reason": null
       }
     ]
   }
   ```
3. On HTTP 200/201/204: mark all sent records as `synced = 1`.
4. On failure: records remain unsynced for the next attempt. No data loss.
5. Every attempt (success or failure) is recorded in `sync_log`.

### ERP-side endpoint
Your Next.js ERP needs a route at `/api/attendance/sync` that accepts this POST body and inserts records into its own attendance table. The `local_id` is provided for deduplication if needed.

---

## Installation & First Run

### Prerequisites
- Python 3.11+
- ZKTeco ZK9500 connected via USB (or `BIOMETRIC_MOCK=true` for testing)

### Setup
```bash
cd attendanceappv1
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment variables (create `.env` or set in shell)
```bash
SECRET_KEY=your-random-32-char-secret
OVERRIDE_PASSWORD=your-override-password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
BIOMETRIC_MOCK=true            # remove when hardware is connected
```

### Run
```bash
python app.py
```
Open browser: **http://127.0.0.1:5050**

Default login: `admin` / `admin@2026` — **change this immediately**.

---

## Security Notes

- The server binds to `127.0.0.1` only — not accessible from the network.
- Passwords are SHA-256 hashed. For production, upgrade to `bcrypt` (add `flask-bcrypt` to requirements).
- The override password is never stored in the database — it lives only in the environment.
- SQLite WAL mode is enabled to safely handle concurrent punch events.
- Biometric templates are stored as BLOB — they cannot be reverse-engineered into fingerprint images.
- The `instance/` folder (containing the database) should be excluded from any remote backup that isn't encrypted.
