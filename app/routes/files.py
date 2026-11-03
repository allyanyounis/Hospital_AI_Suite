import os
import mimetypes
from flask import Blueprint, abort, current_app, send_from_directory
from werkzeug.security import safe_join

from app.models import User, Doctor, Patient, Appointment, MedicalDocument, Prescription, Refund
from app.utils.auth import get_current_user
from app.utils.admin_permissions import is_super_admin, has_panel_permission

files_bp = Blueprint('files', __name__, url_prefix='/files')


def _stream_private_file(rel_path: str):
    """Safely stream a private file from PRIVATE_UPLOAD_FOLDER with security headers."""
    if not rel_path:
        abort(404)

    # Clean and normalize path
    clean = rel_path.replace('\\', '/')
    for prefix in ('uploads/', 'static/uploads/', 'static/prescriptions/'):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]

    # Explicit directory traversal check
    if '..' in clean or clean.startswith('/'):
        abort(404)

    private_base = current_app.config.get(
        'PRIVATE_UPLOAD_FOLDER',
        os.path.join(current_app.instance_path, 'private_uploads')
    )

    full_path = safe_join(private_base, clean)
    if not full_path or not os.path.isfile(full_path):
        # Fallback check across private subfolders by basename
        found = None
        base_name = os.path.basename(clean)
        for sub in ('cnic', 'degrees', 'payment_screenshots', 'prescriptions', 'live_photos', 'medical_documents'):
            cand = safe_join(private_base, sub, base_name)
            if cand and os.path.isfile(cand):
                found = cand
                break
        if not found:
            abort(404)
        full_path = found

    # Ensure path did not escape private_base
    try:
        if os.path.commonpath([os.path.abspath(full_path), os.path.abspath(private_base)]) != os.path.abspath(private_base):
            abort(404)
    except ValueError:
        abort(404)

    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)

    # Determine mime-type & content disposition
    mime_type, _ = mimetypes.guess_type(filename)
    is_image = bool(mime_type and mime_type.startswith('image/'))
    as_attachment = not is_image

    response = send_from_directory(directory, filename, as_attachment=as_attachment)
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@files_bp.route('/identity/<int:user_id>/<string:side>')
def serve_identity(user_id: int, side: str):
    """Serve national identity document (CNIC front/back or doctor live photo) with RBAC."""
    side_lower = (side or '').lower().strip()
    if side_lower not in ('front', 'back', 'live', 'live_photo'):
        abort(404)

    target_user = User.query.get(user_id)
    if not target_user:
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    file_rel_path = None

    if target_user.role == 'patient':
        profile = target_user.patient_profile
        if not profile:
            abort(404)

        if side_lower == 'front':
            file_rel_path = profile.cnic_front_image
        elif side_lower == 'back':
            file_rel_path = profile.cnic_back_image
        else:
            abort(404)

        # RBAC Check: Patient owner or admin with patients view permission
        is_owner = (current.id == target_user.id)
        is_admin_allowed = (current.role == 'admin' and (is_super_admin(current) or has_panel_permission(current, 'patients', 'view')))
        if not (is_owner or is_admin_allowed):
            abort(404)

    elif target_user.role == 'doctor':
        profile = target_user.doctor_profile
        if not profile:
            abort(404)

        if side_lower == 'front':
            file_rel_path = profile.cnic_front_image
        elif side_lower == 'back':
            file_rel_path = profile.cnic_back_image
        elif side_lower in ('live', 'live_photo'):
            file_rel_path = profile.live_photo
        else:
            abort(404)

        # RBAC Check: Doctor owner or admin with doctors view permission
        is_owner = (current.id == target_user.id)
        is_admin_allowed = (current.role == 'admin' and (is_super_admin(current) or has_panel_permission(current, 'doctors', 'view')))
        if not (is_owner or is_admin_allowed):
            abort(404)
    else:
        abort(404)

    if not file_rel_path:
        abort(404)

    return _stream_private_file(file_rel_path)


@files_bp.route('/degree/<int:doctor_id>/<int:index>')
def serve_degree(doctor_id: int, index: int):
    """Serve doctor educational degree/credential with RBAC."""
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        abort(404)

    degrees = doctor.degree_documents or []
    if index < 0 or index >= len(degrees):
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    # RBAC Check: Doctor owner or admin with doctors view permission
    is_owner = (current.id == doctor.user_id)
    is_admin_allowed = (current.role == 'admin' and (is_super_admin(current) or has_panel_permission(current, 'doctors', 'view')))
    if not (is_owner or is_admin_allowed):
        abort(404)

    return _stream_private_file(degrees[index])


@files_bp.route('/payment-proof/<int:appointment_id>')
def serve_payment_proof(appointment_id: int):
    """Serve appointment manual payment receipt with RBAC."""
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        abort(404)

    proof_path = appointment.payment_screenshot
    if not proof_path or proof_path.startswith('safepay_'):
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    # RBAC Check: Patient owner who booked the appointment or admin with payments view permission
    is_owner = (
        current.role == 'patient'
        and hasattr(current, 'patient_profile')
        and current.patient_profile
        and current.patient_profile.id == appointment.patient_id
    )
    is_admin_allowed = (
        current.role == 'admin'
        and (is_super_admin(current) or has_panel_permission(current, 'payments', 'view'))
    )
    if not (is_owner or is_admin_allowed):
        abort(404)

    return _stream_private_file(proof_path)


@files_bp.route('/medical-document/<int:doc_id>')
def serve_medical_document(doc_id: int):
    """Serve patient clinical medical document with RBAC."""
    doc = MedicalDocument.query.get(doc_id)
    if not doc:
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    # RBAC Check:
    # 1. Patient owner
    is_owner = (
        current.role == 'patient'
        and hasattr(current, 'patient_profile')
        and current.patient_profile
        and current.patient_profile.id == doc.patient_id
    )

    # 2. Treating doctor with active appointment and visibility enabled
    is_doctor_allowed = False
    if current.role == 'doctor' and hasattr(current, 'doctor_profile') and current.doctor_profile:
        if doc.is_visible_to_doctor:
            has_appointment = Appointment.query.filter(
                Appointment.doctor_id == current.doctor_profile.id,
                Appointment.patient_id == doc.patient_id,
                Appointment.status != 'cancelled'
            ).first() is not None
            if has_appointment:
                is_doctor_allowed = True

    # 3. Admin with patients view permission
    is_admin_allowed = (
        current.role == 'admin'
        and (is_super_admin(current) or has_panel_permission(current, 'patients', 'view'))
    )

    if not (is_owner or is_doctor_allowed or is_admin_allowed):
        abort(404)

    return _stream_private_file(doc.file_path)


@files_bp.route('/prescription-pdf/<int:prescription_id>')
def serve_prescription_pdf(prescription_id: int):
    """Serve prescription PDF with RBAC."""
    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    # RBAC Check:
    # 1. Patient owner
    is_patient = (
        current.role == 'patient'
        and hasattr(current, 'patient_profile')
        and current.patient_profile
        and prescription.appointment
        and current.patient_profile.id == prescription.appointment.patient_id
    )

    # 2. Issuing doctor
    is_doctor = (
        current.role == 'doctor'
        and hasattr(current, 'doctor_profile')
        and current.doctor_profile
        and prescription.appointment
        and current.doctor_profile.id == prescription.appointment.doctor_id
    )

    # 3. Admin with appointments view permission
    is_admin = (
        current.role == 'admin'
        and (is_super_admin(current) or has_panel_permission(current, 'appointments', 'view'))
    )

    if not (is_patient or is_doctor or is_admin):
        abort(404)

    pdf_rel_path = prescription.pdf_path
    private_base = current_app.config.get(
        'PRIVATE_UPLOAD_FOLDER',
        os.path.join(current_app.instance_path, 'private_uploads')
    )

    # Generate on demand if missing
    needs_generation = False
    if not pdf_rel_path:
        needs_generation = True
    else:
        clean = pdf_rel_path.replace('\\', '/')
        for prefix in ('static/prescriptions/', 'prescriptions/'):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        check_path = os.path.join(private_base, 'prescriptions', os.path.basename(clean))
        if not os.path.isfile(check_path):
            needs_generation = True

    if needs_generation:
        from app.utils.pdf_generator import generate_prescription_pdf
        generate_prescription_pdf(prescription)
        pdf_rel_path = prescription.pdf_path

    return _stream_private_file(pdf_rel_path)


@files_bp.route('/refund-proof/<int:refund_id>')
def serve_refund_proof(refund_id: int):
    """Serve refund bank transfer proof with RBAC."""
    refund = Refund.query.get(refund_id)
    if not refund or not refund.payout_detail or not refund.payout_detail.admin_proof_path:
        abort(404)

    current = get_current_user()
    if not current:
        abort(404)

    # RBAC Check:
    # 1. Patient owner of the appointment refund
    is_owner = (
        current.role == 'patient'
        and hasattr(current, 'patient_profile')
        and current.patient_profile
        and refund.appointment
        and current.patient_profile.id == refund.appointment.patient_id
    )

    # 2. Admin with accounts view permission (or super admin)
    is_admin = (
        current.role == 'admin'
        and (is_super_admin(current) or has_panel_permission(current, 'accounts', 'view'))
    )

    if not (is_owner or is_admin):
        abort(404)

    return _stream_private_file(refund.payout_detail.admin_proof_path)
