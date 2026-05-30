import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Automatically set by Vercel runtime
IS_VERCEL = bool(os.environ.get('VERCEL'))

class Config:
    # ── Flask session ─────────────────────────────────────────────────────────
    SECRET_KEY             = os.environ.get('SECRET_KEY', 'change-this-in-production-32chars!')
    SESSION_PERMANENT      = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    # Scope session cookie to /attendance so it doesn't bleed into ERP paths.
    # Set SESSION_COOKIE_PATH=/attendance in Vercel env vars.
    SESSION_COOKIE_PATH    = os.environ.get('SESSION_COOKIE_PATH', '/')
    SESSION_COOKIE_SECURE  = IS_VERCEL          # HTTPS only on Vercel
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ── Database ──────────────────────────────────────────────────────────────
    # Vercel:  set DATABASE_URL to Supabase connection pooler (port 6543, Transaction mode)
    #   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    # Local:   leave unset → SQLite punch station
    DATABASE_URL  = os.environ.get('DATABASE_URL', '')
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'attendance.db')

    # ── Biometric device (ZKTeco ZK9500) ─────────────────────────────────────
    BIOMETRIC_DEVICE_INDEX       = 0
    BIOMETRIC_SDK_PATH           = os.environ.get('ZK_SDK_PATH', '')
    BIOMETRIC_MOCK_MODE          = IS_VERCEL or (os.environ.get('BIOMETRIC_MOCK', 'false').lower() == 'true')
    BIOMETRIC_TEMPLATE_SIZE      = 2048
    BIOMETRIC_MATCH_THRESHOLD    = 50
    BIOMETRIC_IDENTIFY_THRESHOLD = 45
    ENROLLMENT_SCANS_REQUIRED    = 3
    FINGER_LABELS = {
        0: 'Right Thumb',  1: 'Right Index',  2: 'Right Middle',
        3: 'Right Ring',   4: 'Right Little', 5: 'Left Thumb',
        6: 'Left Index',   7: 'Left Middle',  8: 'Left Ring',
        9: 'Left Little',
    }
    PRIMARY_FINGER = 1
    BACKUP_FINGER  = 6

    # ── Attendance ────────────────────────────────────────────────────────────
    DEFAULT_GRACE_MINUTES  = 10
    PUNCH_COOLDOWN_MINUTES = 1

    # ── Override password (super admin secondary auth) ────────────────────────
    OVERRIDE_PASSWORD = os.environ.get('OVERRIDE_PASSWORD', 'override@2026')

    # ── Face recognition ──────────────────────────────────────────────────────
    FACE_MATCH_THRESHOLD = 0.55
    FACE_SPOOF_MIN_SCORE = 60
    FACE_ENROLL_FRAMES   = 3
    FACE_MOCK_MODE       = IS_VERCEL or (os.environ.get('FACE_MOCK', 'false').lower() == 'true')

    # ── Local dev server ──────────────────────────────────────────────────────
    HOST  = '127.0.0.1'
    PORT  = 5050
    DEBUG = False
