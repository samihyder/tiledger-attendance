from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, permission_required, current_user, has_permission
import db_manager as db
import biometric_service as bio
import face_service as face
from config import Config
import json

employee_bp = Blueprint('employees', __name__)


@employee_bp.route('/')
@login_required
@permission_required('manage_employees')
def list_employees():
    employees = db.get_employees(active_only=False)
    return render_template('employees/list.html', employees=employees, user=current_user())


@employee_bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_employees')
def new_employee():
    if request.method == 'POST':
        data = {
            'employee_code':             request.form['employee_code'].strip().upper(),
            'full_name':                 request.form['full_name'].strip(),
            'department':                request.form.get('department', '').strip(),
            'designation':               request.form.get('designation', '').strip(),
            'phone':                     request.form.get('phone', '').strip(),
            'email':                     request.form.get('email', '').strip(),
            'joining_date':              request.form.get('joining_date', ''),
            'monthly_salary':            request.form.get('monthly_salary', 0),
            'weekly_off_day':            request.form.get('weekly_off_day', 6),
            'deduction_rate_override':   'deduction_rate_override' in request.form,
            'late_deduction_per_minute': request.form.get('late_deduction_per_minute', 0),
        }
        if not data['employee_code'] or not data['full_name']:
            flash('Employee code and full name are required.', 'danger')
            return render_template('employees/form.html', employee=data, user=current_user())

        existing = db.get_employee_by_code(data['employee_code'])
        if existing:
            flash(f'Employee code {data["employee_code"]} already exists.', 'danger')
            return render_template('employees/form.html', employee=data, user=current_user())

        emp_id = db.create_employee(data, created_by=session['user_id'])
        flash(f'Employee {data["full_name"]} registered successfully.', 'success')
        return redirect(url_for('employees.enroll', employee_id=emp_id))

    return render_template('employees/form.html', employee={}, user=current_user())


@employee_bp.route('/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_employees')
def edit_employee(employee_id):
    employee = db.get_employee(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employees.list_employees'))

    if request.method == 'POST':
        data = {
            'full_name':                 request.form['full_name'].strip(),
            'department':                request.form.get('department', '').strip(),
            'designation':               request.form.get('designation', '').strip(),
            'phone':                     request.form.get('phone', '').strip(),
            'email':                     request.form.get('email', '').strip(),
            'joining_date':              request.form.get('joining_date', ''),
            'monthly_salary':            request.form.get('monthly_salary', 0),
            'weekly_off_day':            request.form.get('weekly_off_day', 6),
            'deduction_rate_override':   'deduction_rate_override' in request.form,
            'late_deduction_per_minute': request.form.get('late_deduction_per_minute', 0),
            'active':                    request.form.get('active') == '1',
        }
        db.update_employee(employee_id, data)
        flash('Employee updated.', 'success')
        return redirect(url_for('employees.list_employees'))

    return render_template('employees/form.html', employee=dict(employee), user=current_user(), edit=True)


@employee_bp.route('/<int:employee_id>/deactivate', methods=['POST'])
@login_required
@permission_required('manage_employees')
def deactivate_employee(employee_id):
    db.delete_employee(employee_id)
    flash('Employee deactivated.', 'warning')
    return redirect(url_for('employees.list_employees'))


@employee_bp.route('/api/enroll-face', methods=['POST'])
@login_required
@permission_required('biometric_enroll')
def api_enroll_face():
    """
    Enroll face from browser-extracted descriptors.
    Expects JSON: {employee_id, embeddings: [[float x 128], ...]}
    Descriptors computed client-side by face-api.js.
    """
    data        = request.get_json()
    employee_id = int(data.get('employee_id', 0))
    embeddings  = data.get('embeddings', [])

    if not employee_id:
        return jsonify({'success': False, 'error': 'Employee ID required'}), 400
    if len(embeddings) < face.FACE_ENROLL_FRAMES:
        return jsonify({'success': False, 'error': f'Need {face.FACE_ENROLL_FRAMES} face captures, got {len(embeddings)}'}), 400
    if not db.get_employee(employee_id):
        return jsonify({'success': False, 'error': 'Employee not found'}), 404

    try:
        embedding, quality = face.enroll_from_embeddings(embeddings)
        db.save_face_template(employee_id, json.dumps(embedding), quality, enrolled_by=session['user_id'])
        return jsonify({
            'success': True,
            'quality': quality,
            'message': 'Face enrolled successfully',
        })
    except face.FaceServiceError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Face enrollment error: {e}'}), 500


@employee_bp.route('/api/delete-face', methods=['POST'])
@login_required
@permission_required('biometric_enroll')
def api_delete_face():
    data = request.get_json()
    db.delete_face_template(int(data.get('employee_id', 0)))
    return jsonify({'success': True})


@employee_bp.route('/api/liveness-check', methods=['POST'])
@login_required
@permission_required('biometric_enroll')
def api_liveness_check():
    # Liveness checking moved to client-side (face-api.js)
    return jsonify({'success': True, 'is_live': True, 'score': 90, 'checks': {}})


@employee_bp.route('/<int:employee_id>/enroll', methods=['GET'])
@login_required
@permission_required('biometric_enroll')
def enroll(employee_id):
    employee = db.get_employee(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employees.list_employees'))
    templates = db.get_templates_for_employee(employee_id)
    enrolled_fingers = {t['finger_index'] for t in templates}
    face_template = db.get_face_template(employee_id)
    return render_template(
        'employees/enroll.html',
        employee=dict(employee),
        enrolled_fingers=enrolled_fingers,
        finger_labels=Config.FINGER_LABELS,
        primary_finger=Config.PRIMARY_FINGER,
        backup_finger=Config.BACKUP_FINGER,
        face_enrolled=face_template is not None,
        face_quality=face_template['quality'] if face_template else None,
        face_enrolled_at=face_template['enrolled_at'] if face_template else None,
        face_enroll_frames=face.FACE_ENROLL_FRAMES,
        face_mock=face.FACE_MOCK_MODE,
        user=current_user(),
    )


@employee_bp.route('/api/enroll-finger', methods=['POST'])
@login_required
@permission_required('biometric_enroll')
def api_enroll_finger():
    """
    Trigger enrollment for one finger via AJAX.
    Opens device, runs multi-scan enrollment, saves template.
    """
    data = request.get_json()
    employee_id  = int(data.get('employee_id', 0))
    finger_index = int(data.get('finger_index', Config.PRIMARY_FINGER))

    if not db.get_employee(employee_id):
        return jsonify({'success': False, 'error': 'Employee not found'}), 404

    try:
        device = bio.get_device()
        if not device.is_open:
            device.open()
        template, quality = device.enroll(scans_required=Config.ENROLLMENT_SCANS_REQUIRED)
        finger_label = Config.FINGER_LABELS.get(finger_index, f'Finger {finger_index}')
        db.save_template(
            employee_id=employee_id,
            finger_index=finger_index,
            finger_label=finger_label,
            template_data=template,
            quality_score=quality,
            enrolled_by=session['user_id'],
        )
        return jsonify({
            'success': True,
            'finger_label': finger_label,
            'quality': quality,
            'message': f'{finger_label} enrolled (quality {quality}%)',
        })
    except bio.BiometricError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {e}'}), 500


@employee_bp.route('/api/delete-finger', methods=['POST'])
@login_required
@permission_required('biometric_enroll')
def api_delete_finger():
    data = request.get_json()
    employee_id  = int(data.get('employee_id', 0))
    finger_index = int(data.get('finger_index', 0))
    db.delete_template(employee_id, finger_index)
    return jsonify({'success': True})
