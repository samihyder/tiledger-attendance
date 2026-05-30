# TiLedger Attendance System

A Flask-based attendance management system with biometric punch-in/out, face recognition, payroll deductions, roster management, and Supabase integration.

Live: [kitchenos.chipyeat.com/attendance](https://kitchenos.chipyeat.com/attendance)

---

## Features

- **Biometric punch** — ZKTeco fingerprint scanner support
- **Face recognition** — anti-spoofing + liveness detection
- **Manual entry** — override with admin password
- **Roster & shifts** — assign shifts, mark holidays
- **Payroll** — late deduction calculation per employee
- **Role-based access** — super_admin, manager, system_admin, store
- **Sync to ERP** — push daily attendance to Supabase (manager time-windowed)
- **Encrypted settings** — ERP credentials stored encrypted, password-locked UI

---

## Roles

| Role | Access |
|---|---|
| `super_admin` | Full access, user management, system settings |
| `manager` | All features except manual entry (requires override password). Sync allowed at 17:00, 23:30, 04:00–05:00 |
| `system_admin` | Employee registration, biometric enrollment |
| `store` | Punch in/out only. Manual entry via override password (emergency) |

---

## Tech Stack

- **Backend** — Python 3.12, Flask
- **Database** — SQLite (local) / Supabase PostgreSQL (Vercel)
- **Deployment** — Vercel (`@vercel/python`)
- **Auth** — Session-based, SHA-256 password hashing

---

## Deployment

### Vercel (Production)

**1. Supabase — run once**

Open your Supabase project → SQL Editor → run `schema_supabase.sql`.

**2. Vercel environment variables**

| Variable | Value |
|---|---|
| `DATABASE_URL` | Supabase → Settings → Database → Connection string → Transaction pooler (port 6543) |
| `SECRET_KEY` | Any 40+ char random string |
| `OVERRIDE_PASSWORD` | Super admin override password |
| `APP_PREFIX` | `/attendance` |
| `SESSION_COOKIE_PATH` | `/attendance` |

**3. ERP path routing (`next.config.js`)**

```js
async rewrites() {
  return [
    {
      source: '/attendance/:path*',
      destination: `${process.env.ATTENDANCE_URL}/attendance/:path*`,
    },
  ]
}
```

Add `ATTENDANCE_URL=https://tiledger-attendance.vercel.app` to ERP's Vercel env vars.

---

### Local (Punch Station)

```bash
# Install full dependencies including face recognition
pip install -r requirements-local.txt

# Run with real biometric hardware
python app.py

# Run without hardware (development)
BIOMETRIC_MOCK=true FACE_MOCK=true python app.py
```

Access at `http://127.0.0.1:5050`

---

## Default Login

| Username | Password | Role |
|---|---|---|
| `admin` | `admin@2026` | Super Admin |
| `manager` | `manager@2026` | Manager |
| `store` | `store@2026` | Store |

> Change all passwords immediately after first login.

---

## Project Structure

```
├── app.py                  # Flask app factory
├── wsgi.py                 # Vercel entry point
├── config.py               # Configuration (env-aware)
├── db_manager.py           # SQLite + PostgreSQL dual-mode DB layer
├── auth.py                 # RBAC, session helpers, override escalation
├── attendance_logic.py     # Punch processing, late calculation
├── sync_service.py         # Supabase sync with manager time windows
├── biometric_service.py    # ZKTeco fingerprint device wrapper
├── face_service.py         # Face recognition + anti-spoofing
├── routes/                 # Flask blueprints
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS / JS
├── schema_supabase.sql     # Supabase PostgreSQL schema (run once)
├── requirements.txt        # Vercel dependencies (flask + psycopg2)
└── requirements-local.txt  # Local dependencies (+ face_recognition, opencv)
```

---

## Sync Windows (Manager)

Manager can only trigger ERP sync during:
- **17:00 – 17:30**
- **23:30 – 00:00**
- **04:00 – 05:00**

Super admin can sync at any time.

---

## Security

- All sensitive settings (API keys) stored XOR-encrypted in database
- Settings page requires super admin login password to unlock
- Manual attendance requires override password for manager/store roles
- Session cookies scoped to `/attendance` path
- HTTPS-only cookies enforced on Vercel (`SESSION_COOKIE_SECURE=True`)
