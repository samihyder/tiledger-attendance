"""
RBAC helpers and session management.

Roles:
  super_admin  — full access; manages users; can activate manual override
  manager      — all features except manual entry; manual entry requires override password
  system_admin — employee registration, biometric enrollment, device settings
  store        — punch in/out and sync to ERP only; manual entry via override password (emergency)

Permission matrix:
  Feature                  super_admin  manager  system_admin  store
  ────────────────────────────────────────────────────────────────────
  View dashboard           ✓            ✓         ✓             ✓
  Punch screen             ✓            ✓         ✓             ✓
  View attendance logs     ✓            ✓         ✓             ✗
  Export attendance        ✓            ✓         ✗             ✗
  Manual attendance        ✓            override  ✗             override
  Roster CRUD              ✓            ✓         ✗             ✗
  Employee CRUD            ✓            ✗         ✓             ✗
  Biometric enrollment     ✓            ✗         ✓             ✗
  Sync to ERP              ✓            ✓         ✗             ✓
  View payroll             ✓            ✓         ✗             ✗
  Manage app users         ✓            ✗         ✗             ✗
  System settings          ✓            ✗         ✗             ✗

  "override" = super admin password required at runtime
"""

from functools import wraps
from flask import session, redirect, url_for, flash, request

ROLE_HIERARCHY = {
    'super_admin':  3,
    'manager':      2,
    'system_admin': 1,
    'store':        0,
}

PERMISSIONS = {
    'view_dashboard':      ['super_admin', 'manager', 'system_admin', 'store'],
    'punch':               ['super_admin', 'manager', 'system_admin', 'store'],
    'view_attendance':     ['super_admin', 'manager', 'system_admin'],
    'export_attendance':   ['super_admin', 'manager'],
    'manual_attendance':   ['super_admin'],
    'roster':              ['super_admin', 'manager'],
    'manage_employees':    ['super_admin', 'manager', 'system_admin'],
    'biometric_enroll':    ['super_admin', 'manager', 'system_admin'],
    'sync':                ['super_admin', 'manager'],
    'view_payroll':        ['super_admin', 'manager'],
    'manage_users':        ['super_admin'],
    'system_settings':     ['super_admin'],
}

# Roles that can access a permission by verifying OVERRIDE_PASSWORD at runtime
OVERRIDE_ESCALATABLE = {
    'manual_attendance': ['manager', 'store'],
}


def current_user() -> dict | None:
    if 'user_id' not in session:
        return None
    return {
        'id':        session['user_id'],
        'username':  session['username'],
        'full_name': session.get('full_name', ''),
        'role':      session['role'],
    }


def has_permission(permission: str) -> bool:
    user = current_user()
    if not user:
        return False
    if user['role'] in PERMISSIONS.get(permission, []):
        return True
    # Escalated access: role is allowed to override AND override is active this session
    if (user['role'] in OVERRIDE_ESCALATABLE.get(permission, [])
            and session.get('override_active', False)):
        return True
    return False


def can_escalate_to(permission: str) -> bool:
    """True if the current user's role can reach this permission via override password."""
    user = current_user()
    if not user:
        return False
    return user['role'] in OVERRIDE_ESCALATABLE.get(permission, [])


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def permission_required(permission: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user():
                flash('Please log in.', 'warning')
                return redirect(url_for('auth.login'))
            if has_permission(permission):
                return f(*args, **kwargs)
            if can_escalate_to(permission):
                return redirect(url_for('auth.request_override',
                                        next=request.url, permission=permission))
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return decorated
    return decorator
