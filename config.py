import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load .env if present (local dev / local server)
_env_file = Path(BASE_DIR) / '.env'
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-32chars!')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')

    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'attendance.db')

    # Biometric device (ZKTeco ZK9500 or compatible)
    BIOMETRIC_DEVICE_INDEX = 0          # USB device index (0 = first connected)
    BIOMETRIC_SDK_PATH = os.environ.get('ZK_SDK_PATH', '')   # path to zkfinger SDK .dll/.so
    BIOMETRIC_MOCK_MODE = os.environ.get('BIOMETRIC_MOCK', 'false').lower() == 'true'
    BIOMETRIC_TEMPLATE_SIZE = 2048      # bytes — ZKTeco standard template size
    BIOMETRIC_MATCH_THRESHOLD = 50     # 0–100; 50 is standard 1:1 match threshold
    BIOMETRIC_IDENTIFY_THRESHOLD = 45  # 1:N matching threshold

    # Enrollment
    ENROLLMENT_SCANS_REQUIRED = 3       # scans per finger during registration
    FINGER_LABELS = {
        0: 'Right Thumb',
        1: 'Right Index',   # primary
        2: 'Right Middle',
        3: 'Right Ring',
        4: 'Right Little',
        5: 'Left Thumb',
        6: 'Left Index',    # backup
        7: 'Left Middle',
        8: 'Left Ring',
        9: 'Left Little',
    }
    PRIMARY_FINGER = 1    # Right Index
    BACKUP_FINGER = 6     # Left Index

    # Attendance
    DEFAULT_GRACE_MINUTES = 10
    PUNCH_COOLDOWN_MINUTES = 1   # prevent duplicate punches within N minutes

    # Super Admin override secondary password
    # Set this via environment variable — never hardcode in production
    OVERRIDE_PASSWORD = os.environ.get('OVERRIDE_PASSWORD', 'override@2026')

    # Attendance Supabase (DB 1) — primary sync target
    SUPABASE_URL         = os.environ.get('SUPABASE_URL', '')
    SUPABASE_ANON_KEY    = os.environ.get('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
    # Use service key for writes; fall back to anon
    SUPABASE_KEY         = os.environ.get('SUPABASE_SERVICE_KEY', '') or os.environ.get('SUPABASE_ANON_KEY', '')
    SUPABASE_TABLE       = os.environ.get('SUPABASE_TABLE', 'attendance_daily')

    # ERP Supabase (DB 2 — kitchenosv2) — full mirror target
    ERP_SUPABASE_URL         = os.environ.get('ERP_SUPABASE_URL', '')
    ERP_SUPABASE_SERVICE_KEY = os.environ.get('ERP_SUPABASE_SERVICE_KEY', '')

    SYNC_BATCH_SIZE = 200          # max records per sync request

    # Face recognition
    FACE_MATCH_THRESHOLD = 0.55      # Euclidean distance — lower = stricter
    FACE_SPOOF_MIN_SCORE = 60        # % of anti-spoofing checks that must pass
    FACE_ENROLL_FRAMES   = 5         # frames averaged during enrollment
    FACE_MOCK_MODE       = os.environ.get('FACE_MOCK', 'false').lower() == 'true'

    # Server — localhost only
    HOST = '127.0.0.1'
    PORT = 5050
    DEBUG = False
