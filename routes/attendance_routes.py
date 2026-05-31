from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import date, datetime
from auth import login_required, permission_required, current_user, can_escalate_to
import db_manager as db
import biometric_service as bio
import face_service as face
import attendance_logic as logic
from config import Config
import json

attendance_bp = Blueprint('attendance', __name__)


def _is_manual_mode_today() -> bool:
    return db.get_manual_mode_date() == date.today().strftime('%Y-%m-%d')


# ──────────────────────────────────────────────────────────────────────────────
# Punch screen
# ──────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/punch')
@login_required
@permission_required('punch')
def punch_screen():
    today = date.today().strftime('%Y-%m-%d')
    recent = db.get_attendance_logs(date_from=today, date_to=today)[:10]
    employees = db.get_employees(active_only=True) if _is_manual_mode_today() else []
    face_count = len(db.get_all_face_templates())
    return render_template(
        'attendance/punch.html',
        recent=recent,
        employees=employees,
        manual_mode=_is_manual_mode_today(),
        face_templates_exist=face_count > 0,
        face_mock=face.FACE_MOCK_MODE,
        today=today,
        user=current_user(),
    )


@attendance_bp.route('/api/toggle-manual-mode', methods=['POST'])
@login_required
def api_toggle_manual_mode():
    user = current_user()
    role = user['role'] if user else ''
    if role not in ('super_admin', 'manager', 'store'):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    data = request.get_json()
    today = date.today().strftime('%Y-%m-%d')
    if _is_manual_mode_today():
        db.disable_manual_mode()
        return jsonify({'success': True, 'manual_mode': False})
    if data.get('password', '') != Config.OVERRIDE_PASSWORD:
        return jsonify({'success': False, 'error': 'Incorrect override password'}), 403
    db.enable_manual_mode(today)
    # Grant override session so manager/store can also use the backdated /manual page
    session['override_active'] = True
    return jsonify({'success': True, 'manual_mode': True, 'message': f'Manual mode enabled for {today}'})


@attendance_bp.route('/api/manual-punch', methods=['POST'])
@login_required
@permission_required('punch')
def api_manual_punch():
    if not _is_manual_mode_today():
        return jsonify({'success': False, 'error': 'Manual mode is not active for today'}), 403
    data = request.get_json()
    employee_id = int(data.get('employee_id', 0))
    if not employee_id:
        return jsonify({'success': False, 'error': 'Select an employee'}), 400
    result = logic.process_manual_day_punch(employee_id, override_by=session['user_id'])
    return jsonify(result), 200 if result['success'] else 400


@attendance_bp.route('/api/face-punch', methods=['POST'])
@login_required
@permission_required('punch')
def api_face_punch():
    """
    Face identification + punch.
    Expects JSON: {embedding: [float x 128]}
    Descriptor extracted client-side by face-api.js.
    """
    data      = request.get_json()
    embedding = data.get('embedding', [])
    if not embedding or len(embedding) != 128:
        return jsonify({'success': False, 'error': 'Invalid face embedding from browser'}), 400

    templates = db.get_all_face_templates()
    if not templates:
        return jsonify({'success': False, 'error': 'No face templates enrolled yet'}), 400

    template_list = [
        {'employee_id': t['employee_id'], 'embedding': t['embedding'],
         'full_name': t['full_name'], 'employee_code': t['employee_code']}
        for t in templates
    ]

    try:
        matched = face.identify(embedding, template_list)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Face recognition error: {e}'}), 500

    if not matched:
        return jsonify({'success': False, 'error': 'Face not recognised — try again or use manual entry'}), 401

    result = logic.process_biometric_punch(matched['employee_id'])
    result['confidence']   = matched.get('confidence', 0)
    result['punch_method'] = 'face'
    return jsonify(result)


@attendance_bp.route('/api/blink-check', methods=['POST'])
@login_required
@permission_required('punch')
def api_blink_check():
    # Blink detection moved to client-side (face-api.js)
    return jsonify({'success': True, 'blink_detected': True})


@attendance_bp.route('/api/biometric-punch', methods=['POST'])
@login_required
@permission_required('punch')
def api_biometric_punch():
    templates = db.get_all_templates()
    if not templates:
        return jsonify({'success': False, 'error': 'No biometric templates enrolled yet'}), 400
    try:
        device = bio.get_device()
        if not device.is_open:
            device.open()
        template_list = [
            {'employee_id': t['employee_id'], 'finger_index': t['finger_index'],
             'template_data': bytes(t['template_data'])}
            for t in templates
        ]
        matched = device.identify(template_list)
        if not matched:
            return jsonify({'success': False, 'error': 'Fingerprint not recognised — try again'}), 401
        result = logic.process_biometric_punch(matched['employee_id'])
        return jsonify(result)
    except bio.BiometricError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Device error: {e}'}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Attendance log
# ──────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/log')
@login_required
@permission_required('view_attendance')
def log():
    today = date.today()
    date_from = request.args.get('date_from', today.strftime('%Y-%m-%d'))
    date_to   = request.args.get('date_to',   today.strftime('%Y-%m-%d'))
    employee_id = request.args.get('employee_id', type=int)

    logs      = db.get_attendance_logs(date_from=date_from, date_to=date_to, employee_id=employee_id)
    employees = db.get_employees()
    summary   = logic.get_daily_summary(date_from) if date_from == date_to else []
    is_super_admin = session.get('role') == 'super_admin'

    return render_template(
        'attendance/log.html',
        logs=logs,
        employees=employees,
        date_from=date_from,
        date_to=date_to,
        selected_employee=employee_id,
        summary=summary,
        is_super_admin=is_super_admin,
        user=current_user(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Edit punch — super admin only
# ──────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/api/edit-punch', methods=['POST'])
@login_required
def api_edit_punch():
    if session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'Super Admin only'}), 403

    data = request.get_json()
    log_id        = int(data.get('log_id', 0))
    new_time_str  = data.get('punch_time', '').strip()

    if not log_id or not new_time_str:
        return jsonify({'success': False, 'error': 'log_id and punch_time are required'}), 400

    punch = db.get_punch(log_id)
    if not punch:
        return jsonify({'success': False, 'error': 'Punch record not found'}), 404

    # Parse and validate new time
    try:
        new_time = datetime.strptime(new_time_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid datetime format'}), 400

    new_time_db = new_time.strftime('%Y-%m-%d %H:%M:%S')

    # Recalculate minutes_late if it's a punch-in
    minutes_late = punch['minutes_late']
    if punch['punch_type'] == 'in' and punch['roster_id']:
        roster = db.get_roster_for_date(punch['employee_id'], new_time.strftime('%Y-%m-%d'))
        if roster and not roster['is_holiday']:
            minutes_late = logic.calculate_minutes_late(
                new_time, roster['shift_start'], roster['grace_minutes']
            )

    db.edit_punch(log_id, new_time_db, edited_by=session['user_id'])

    db.update_punch_minutes_late(log_id, minutes_late)

    return jsonify({
        'success': True,
        'log_id': log_id,
        'new_punch_time': new_time_db,
        'minutes_late': minutes_late,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Backdated correction (manual entry page — no roster enforcement)
# ──────────────────────────────────────────────────────────────────────────────

@attendance_bp.route('/manual', methods=['GET', 'POST'])
@login_required
@permission_required('manual_attendance')
def manual():
    employees = db.get_employees()

    if request.method == 'POST':
        employee_id = request.form.get('employee_id', type=int)
        punch_type  = request.form.get('punch_type', 'in')
        punch_time  = request.form.get('punch_time', '').strip()
        reason      = request.form.get('reason', '').strip()

        if not employee_id or not punch_time or not reason:
            flash('Employee, punch time, and reason are all required.', 'danger')
        else:
            result = logic.process_manual_punch(
                employee_id=employee_id,
                punch_type=punch_type,
                punch_time_str=punch_time,
                override_reason=reason,
                override_by=session['user_id'],
            )
            if result['success']:
                late_msg = f' ({result["minutes_late"]} min late)' if result['minutes_late'] else ''
                flash(f'Correction recorded for {result["employee_name"]}{late_msg}.', 'success')
                return redirect(url_for('attendance.log'))
            else:
                flash(result.get('error', 'Failed to record punch.'), 'danger')

    return render_template(
        'attendance/manual.html',
        employees=employees,
        now=datetime.now().strftime('%Y-%m-%dT%H:%M'),
        user=current_user(),
    )
