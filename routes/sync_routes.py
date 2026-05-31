from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, permission_required, current_user
import db_manager as db
import sync_service
import json

_SETTINGS_UNLOCK_KEY = 'sync_settings_unlocked'

sync_bp = Blueprint('sync', __name__)


@sync_bp.route('/')
@login_required
@permission_required('sync')
def sync_status():
    role           = session.get('role', '')
    unsynced_count = len(db.get_unsynced_logs())
    history        = db.get_sync_history(limit=50)
    window_status  = sync_service.manager_window_status() if role == 'manager' else None

    # Parse sync_detail JSON for display
    for h in history:
        h = dict(h)
    history_parsed = []
    for h in history:
        row = dict(h)
        if row.get('sync_detail'):
            try:
                row['detail_records'] = json.loads(row['sync_detail'])
            except Exception:
                row['detail_records'] = []
        else:
            row['detail_records'] = []
        history_parsed.append(row)

    return render_template(
        'sync/status.html',
        unsynced_count=unsynced_count,
        history=history_parsed,
        window_status=window_status,
        role=role,
        user=current_user(),
    )


@sync_bp.route('/run', methods=['POST'])
@login_required
@permission_required('sync')
def run_sync():
    role   = session.get('role', 'super_admin')
    result = sync_service.sync_attendance(synced_by=session['user_id'], role=role)

    if result['status'] == 'window_denied':
        flash(result['error'], 'warning')
    elif result['success']:
        if result['sent'] == 0:
            flash('Nothing to sync — all records are up to date.', 'info')
        else:
            flash(f'Sync complete — {result["sent"]} daily record(s) sent to ERP.', 'success')
    else:
        flash(f'Sync failed: {result["error"]}', 'danger')

    return redirect(url_for('sync.sync_status'))


@sync_bp.route('/api/run', methods=['POST'])
@login_required
@permission_required('sync')
def api_run_sync():
    role   = session.get('role', 'super_admin')
    result = sync_service.sync_attendance(synced_by=session['user_id'], role=role)
    return jsonify(result)


# ──────────────────────────────────────────────────────────────────────────────
# ERP sync settings — super_admin only, password-locked
# ──────────────────────────────────────────────────────────────────────────────

@sync_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@permission_required('system_settings')
def sync_settings():
    unlocked = session.get(_SETTINGS_UNLOCK_KEY, False)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'unlock':
            password = request.form.get('password', '')
            user = db.get_user(session['username'])
            if user and db.verify_password(password, user['password_hash']):
                session[_SETTINGS_UNLOCK_KEY] = True
                flash('Settings unlocked.', 'success')
            else:
                flash('Incorrect password.', 'danger')
            return redirect(url_for('sync.sync_settings'))

        if action == 'lock':
            session.pop(_SETTINGS_UNLOCK_KEY, None)
            flash('Settings locked.', 'info')
            return redirect(url_for('sync.sync_settings'))

        if action == 'save':
            if not unlocked:
                flash('Unlock settings before saving.', 'danger')
                return redirect(url_for('sync.sync_settings'))
            url     = request.form.get('supabase_url', '').strip()
            api_key = request.form.get('supabase_key', '').strip()
            table   = request.form.get('supabase_table', '').strip()
            if not url or not table:
                flash('Attendance Supabase URL and table name are required.', 'danger')
                return redirect(url_for('sync.sync_settings'))
            if not api_key:
                existing = db.get_sync_settings()
                api_key  = existing['api_key']
            db.save_sync_settings(url, api_key, table)
            flash('Attendance Supabase settings saved.', 'success')
            session.pop(_SETTINGS_UNLOCK_KEY, None)
            return redirect(url_for('sync.sync_settings'))

        if action == 'save_erp':
            if not unlocked:
                flash('Unlock settings before saving.', 'danger')
                return redirect(url_for('sync.sync_settings'))
            erp_url = request.form.get('erp_supabase_url', '').strip()
            erp_key = request.form.get('erp_supabase_key', '').strip()
            if erp_url and not erp_key:
                existing = db.get_erp_sync_settings()
                erp_key  = existing['api_key']
            db.save_erp_sync_settings(erp_url, erp_key)
            flash('ERP Supabase settings saved.', 'success')
            session.pop(_SETTINGS_UNLOCK_KEY, None)
            return redirect(url_for('sync.sync_settings'))

    # GET — read settings for display
    raw = db.get_sync_settings_display()
    settings = {
        'url':     raw['url'],
        'table':   raw['table'],
        'api_key': db.decrypt_setting(raw['api_key_enc']) if (unlocked and raw['api_key_enc']) else '',
        'has_key': bool(raw['api_key_enc']),
    }
    erp_raw = db.get_erp_sync_settings_display()
    erp_settings = {
        'url':     erp_raw['url'],
        'api_key': db.decrypt_setting(erp_raw['api_key_enc']) if (unlocked and erp_raw['api_key_enc']) else '',
        'has_key': bool(erp_raw['api_key_enc']),
    }
    return render_template(
        'sync/settings.html',
        unlocked=unlocked,
        settings=settings,
        erp_settings=erp_settings,
        user=current_user(),
    )
