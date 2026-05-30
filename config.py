import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# True when running on Vercel (set automatically by the Vercel runtime)
IS_VERCEL = bool(os.environ.get('VERCEL'))

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-32chars!')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ── Database ──────────────────────────────────────────────────────────────
    # Set DATABASE_URL to Supabase connection pooler URI for Vercel/cloud.
    # Without it the app uses local SQLite (punch station mode).
    #
    # Supabase pooler URL format (Transaction mode, port 6543):
    #   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    DATABASE_URL  = os.environ.get('DATABASE_URL', '')
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'attendance.db')

    # ── Biometric device (ZKTeco ZK9500) ─────────────────────────────────────
    BIOMETRIC_DEVICE_INDEX       = 0
    BIOMETRIC_SDK_PATH           = os.environ.get('ZK_SDK_PATH', '')
    # On Vercel / cloud: always mock (no physical hardware). Locally: requires BIOMETRIC_MOCK=true.
    BIOMETRIC_MOCK_MODE          = IS_VERCEL or (os.environ.get('BIOMETRIC_MOCK', 'false').lower() == 'true')
    BIOMETRIC_TEMPLATE_SIZE      = 2048
    BIOMETRIC_MATCH_THRESHOLD    = 50
    BIOMETRIC_IDENTIFY_THRESHOLD = 45

    # Enrollment
    ENROLLMENT_SCANS_REQUIRED = 3
    FINGER_LABELS = {
        0: 'Right Thumb',  1: 'Right Index',  2: 'Right Middle',
        3: 'Right Ring',   4: 'Right Little',  5: 'Left Thumb',
        6: 'Left Index',   7: 'Left Middle',   8: 'Left Ring',
        9: 'Left Little',
    }
    PRIMARY_FINGER = 1
    BACKUP_FINGER  = 6

    # ── Attendance ────────────────────────────────────────────────────────────
    DEFAULT_GRACE_MINUTES  = 10
    PUNCH_COOLDOWN_MINUTES = 1

    # ── Super Admin override secondary password ───────────────────────────────
    OVERRIDE_PASSWORD = os.environ.get('OVERRIDE_PASSWORD', 'override@2026')

    # ── Supabase sync (DB settings take precedence; env vars are fallback) ────
    SUPABASE_URL   = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY   = (os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
                      or os.environ.get('SUPABASE_ANON_KEY', ''))
    SUPABASE_TABLE = os.environ.get('SUPABASE_TABLE', 'attendance_daily')
    SYNC_BATCH_SIZE = 200

    # ── Face recognition ──────────────────────────────────────────────────────
    FACE_MATCH_THRESHOLD = 0.55
    FACE_SPOOF_MIN_SCORE = 60
    FACE_ENROLL_FRAMES   = 3
    # On Vercel / cloud: always mock. Locally: requires FACE_MOCK=true to use mock.
    FACE_MOCK_MODE = IS_VERCEL or (os.environ.get('FACE_MOCK', 'false').lower() == 'true')

    # ── Local server ──────────────────────────────────────────────────────────
    HOST  = '127.0.0.1'
    PORT  = 5050
    DEBUG = False
