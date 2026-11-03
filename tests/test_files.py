import os
import pytest
from app.models import User, Patient, Doctor, Appointment, MedicalDocument, Prescription, Refund, RefundPayoutDetail, Admin, AdminPanelGrant
from werkzeug.security import generate_password_hash
from datetime import date, time, datetime
import itertools

_seq = itertools.count(100)


def get_unique_suffix():
    return f"{int(datetime.utcnow().timestamp())}{next(_seq)}"


@pytest.fixture
def private_files_env(app):
    """Ensure private uploads directory has dummy test files."""
    priv_base = app.config.get('PRIVATE_UPLOAD_FOLDER', os.path.join(app.instance_path, 'private_uploads'))
    os.makedirs(os.path.join(priv_base, 'cnic'), exist_ok=True)
    os.makedirs(os.path.join(priv_base, 'degrees'), exist_ok=True)
    os.makedirs(os.path.join(priv_base, 'payment_screenshots'), exist_ok=True)
    os.makedirs(os.path.join(priv_base, 'medical_documents', '999'), exist_ok=True)
    os.makedirs(os.path.join(priv_base, 'prescriptions'), exist_ok=True)
    os.makedirs(os.path.join(priv_base, 'refund_proofs'), exist_ok=True)

    with open(os.path.join(priv_base, 'cnic', 'test_cnic_front.jpg'), 'wb') as f:
        f.write(b'FAKE_CNIC_FRONT_BYTES')
    with open(os.path.join(priv_base, 'cnic', 'test_doc_cnic.jpg'), 'wb') as f:
        f.write(b'FAKE_DOC_CNIC_BYTES')
    with open(os.path.join(priv_base, 'degrees', 'test_degree.pdf'), 'wb') as f:
        f.write(b'%PDF-1.4 FAKE_DEGREE_PDF')
    with open(os.path.join(priv_base, 'payment_screenshots', 'test_proof.png'), 'wb') as f:
        f.write(b'FAKE_PAYMENT_PROOF_PNG')
    with open(os.path.join(priv_base, 'medical_documents', '999', 'test_report.pdf'), 'wb') as f:
        f.write(b'%PDF-1.4 FAKE_MEDICAL_REPORT')
    with open(os.path.join(priv_base, 'prescriptions', 'test_rx.pdf'), 'wb') as f:
        f.write(b'%PDF-1.4 FAKE_PRESCRIPTION_PDF')
    with open(os.path.join(priv_base, 'refund_proofs', 'test_refund_transfer.png'), 'wb') as f:
        f.write(b'FAKE_REFUND_PROOF_PNG')

    return priv_base


def _create_staff_admin(db_session, panel_key: str, name_suffix: str):
    """Helper to create a staff admin with only one specific panel grant."""
    s = get_unique_suffix()
    user = User(
        name=f'Staff {name_suffix}',
        email=f'staff.{name_suffix}.{s}@example.com',
        phone=f'+92300{s[-7:]}',
        cnic=f'35201-{s[-7:]}-1',
        role='admin',
        is_active=True,
        password_hash=generate_password_hash('Password123!')
    )
    db_session.add(user)
    db_session.commit()

    admin_profile = Admin(user_id=user.id, admin_level='staff', staff_role='staff')
    db_session.add(admin_profile)
    db_session.commit()

    if panel_key:
        grant = AdminPanelGrant(admin_id=admin_profile.id, panel_key=panel_key, can_view=True)
        db_session.add(grant)
        db_session.commit()

    return user


def _create_doctor(db_session, name_suffix: str):
    """Helper to create a fully valid doctor user and profile."""
    s = get_unique_suffix()
    user = User(
        name=f'Dr {name_suffix}',
        email=f'doc.{name_suffix}.{s}@example.com',
        phone=f'+92322{s[-7:]}',
        cnic=f'35201-{s[-7:]}-9',
        role='doctor',
        is_active=True,
        password_hash=generate_password_hash('Password123!')
    )
    db_session.add(user)
    db_session.commit()
    doc = Doctor(
        user_id=user.id,
        category='Cardiologist',
        specialization='Cardiology',
        experience=5.0,
        pmc_code=f'PMC-TEST-{s[-6:]}',
        education='MBBS, FCPS',
        bio='Experienced Specialist',
        city='Lahore',
        location='Gulberg',
        is_approved=True
    )
    db_session.add(doc)
    db_session.commit()
    return user, doc


# ==============================================================================
# 1. Patient CNIC Matrix
# ==============================================================================
def test_serve_patient_cnic_rbac_matrix(client, test_patient, test_doctor, test_admin, db_session, private_files_env):
    """Matrix test: Patient CNIC access permissions."""
    patient_model = test_patient.patient_profile
    patient_model.cnic_front_image = 'cnic/test_cnic_front.jpg'
    db_session.commit()

    url = f"/files/identity/{test_patient.id}/front"

    # Cell 1: Anonymous -> 404
    client.get('/auth/logout')
    assert client.get(url).status_code == 404

    # Cell 2: Owner patient -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
    res = client.get(url)
    assert res.status_code == 200
    assert res.data == b'FAKE_CNIC_FRONT_BYTES'
    assert res.headers.get('Cache-Control') == 'private, no-store'

    # Cell 3: Other patient -> 404
    s = get_unique_suffix()
    other_patient_user = User(
        name='Other Patient', email=f'other.pat.{s}@example.com',
        phone=f'+92311{s[-7:]}', cnic=f'35201-{s[-7:]}-2',
        role='patient', is_active=True, password_hash=generate_password_hash('Password123!')
    )
    db_session.add(other_patient_user)
    db_session.commit()
    other_patient = Patient(user_id=other_patient_user.id)
    db_session.add(other_patient)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = other_patient_user.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 404

    # Cell 4: Doctor -> 404
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 404

    # Cell 5: Super admin -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Cell 6: Staff admin WITH 'patients' panel -> 200
    staff_patients = _create_staff_admin(db_session, 'patients', 'with_patients')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_patients.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Cell 7: Staff admin WITHOUT 'patients' panel (e.g. 'doctors' panel only) -> 404
    staff_doctors = _create_staff_admin(db_session, 'doctors', 'without_patients')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_doctors.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 404


# ==============================================================================
# 2. Doctor CNIC & Degree Matrix
# ==============================================================================
def test_serve_doctor_cnic_and_degree_rbac_matrix(client, test_doctor, test_patient, test_admin, db_session, private_files_env):
    """Matrix test: Doctor CNIC and Degree access permissions."""
    doc_model = test_doctor.doctor_profile
    doc_model.cnic_front_image = 'cnic/test_doc_cnic.jpg'
    doc_model.degree_documents = ['degrees/test_degree.pdf']
    db_session.commit()

    cnic_url = f"/files/identity/{test_doctor.id}/front"
    degree_url = f"/files/degree/{doc_model.id}/0"

    # Other doctor setup
    other_doc_user, other_doc = _create_doctor(db_session, 'OtherDoc')

    # Staff admins
    staff_doctors = _create_staff_admin(db_session, 'doctors', 'doc_verifier')
    staff_accounts = _create_staff_admin(db_session, 'accounts', 'no_doc_access')

    for target_url, is_pdf in [(cnic_url, False), (degree_url, True)]:
        # Anonymous -> 404
        client.get('/auth/logout')
        assert client.get(target_url).status_code == 404

        # Owner doctor -> 200
        with client.session_transaction() as sess:
            sess['user_id'] = test_doctor.id
            sess['user_role'] = 'doctor'
        res = client.get(target_url)
        assert res.status_code == 200
        if is_pdf:
            assert res.headers.get('Content-Disposition', '').startswith('attachment')
        else:
            assert res.headers.get('Content-Disposition', '').startswith('inline')

        # Other doctor -> 404
        with client.session_transaction() as sess:
            sess['user_id'] = other_doc_user.id
            sess['user_role'] = 'doctor'
        assert client.get(target_url).status_code == 404

        # Patient -> 404
        with client.session_transaction() as sess:
            sess['user_id'] = test_patient.id
            sess['user_role'] = 'patient'
        assert client.get(target_url).status_code == 404

        # Super admin -> 200
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['user_role'] = 'admin'
        assert client.get(target_url).status_code == 200

        # Staff with 'doctors' panel -> 200
        with client.session_transaction() as sess:
            sess['user_id'] = staff_doctors.id
            sess['user_role'] = 'admin'
        assert client.get(target_url).status_code == 200

        # Staff WITHOUT 'doctors' panel -> 404
        with client.session_transaction() as sess:
            sess['user_id'] = staff_accounts.id
            sess['user_role'] = 'admin'
        assert client.get(target_url).status_code == 404


# ==============================================================================
# 3. Payment Screenshot Matrix
# ==============================================================================
def test_serve_payment_proof_rbac_matrix(client, test_patient, test_doctor, test_admin, db_session, private_files_env):
    """Matrix test: Payment screenshot (the paying patient or staff with payments panel; NOT the doctor)."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date=date(2026, 12, 1),
        appointment_time=time(10, 0),
        appointment_type='video',
        status='pending',
        charges=1500.0,
        disease_category='General',
        payment_status='pending',
        payment_screenshot='payment_screenshots/test_proof.png'
    )
    db_session.add(appt)
    db_session.commit()

    url = f"/files/payment-proof/{appt.id}"

    # Anonymous -> 404
    client.get('/auth/logout')
    assert client.get(url).status_code == 404

    # Paying patient -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
    res = client.get(url)
    assert res.status_code == 200

    # The appointment's doctor -> 404 (Explicit Rule: NOT the doctor!)
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 404

    # Other patient -> 404
    s = get_unique_suffix()
    other_pat_user = User(
        name='Other Patient P', email=f'other.pat.{s}@example.com',
        phone=f'+92333{s[-7:]}', cnic=f'35201-{s[-7:]}-4',
        role='patient', is_active=True, password_hash=generate_password_hash('Password123!')
    )
    db_session.add(other_pat_user)
    db_session.commit()
    other_pat = Patient(user_id=other_pat_user.id)
    db_session.add(other_pat)
    db_session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = other_pat_user.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 404

    # Super admin -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff with 'payments' panel -> 200
    staff_payments = _create_staff_admin(db_session, 'payments', 'payment_officer')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_payments.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff WITHOUT 'payments' panel (e.g. 'doctors' only) -> 404
    staff_doctors = _create_staff_admin(db_session, 'doctors', 'no_pay_access')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_doctors.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 404


# ==============================================================================
# 4. Medical Document Matrix
# ==============================================================================
def test_serve_medical_document_rbac_matrix(client, test_patient, test_doctor, test_admin, db_session, private_files_env):
    """Matrix test: Patient clinical medical document."""
    # Ensure active appointment relationship exists between test_patient and test_doctor
    existing_appt = Appointment.query.filter_by(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id
    ).first()
    if not existing_appt:
        existing_appt = Appointment(
            patient_id=test_patient.patient_profile.id,
            doctor_id=test_doctor.doctor_profile.id,
            appointment_date=date(2026, 12, 1),
            appointment_time=time(11, 0),
            appointment_type='video',
            status='approved',
            charges=1500.0,
            disease_category='General',
            payment_status='paid'
        )
        db_session.add(existing_appt)
        db_session.commit()

    med_doc = MedicalDocument(
        patient_id=test_patient.patient_profile.id,
        filename='test_report.pdf',
        file_path='medical_documents/999/test_report.pdf',
        file_type='pdf',
        file_size=1024,
        is_visible_to_doctor=True
    )
    db_session.add(med_doc)
    db_session.commit()

    url = f"/files/medical-document/{med_doc.id}"

    # Anonymous -> 404
    client.get('/auth/logout')
    assert client.get(url).status_code == 404

    # Owner patient -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 200

    # Treating doctor WITH active appointment -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 200

    # Treating doctor when document visibility is revoked -> 404
    med_doc.is_visible_to_doctor = False
    db_session.commit()
    assert client.get(url).status_code == 404
    med_doc.is_visible_to_doctor = True
    db_session.commit()

    # Unrelated doctor without active appointment -> 404
    unrelated_doc_user, unrelated_doc = _create_doctor(db_session, 'UnrelatedM')
    with client.session_transaction() as sess:
        sess['user_id'] = unrelated_doc_user.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 404

    # Super admin -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff with 'patients' panel -> 200
    staff_patients = _create_staff_admin(db_session, 'patients', 'patient_lead')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_patients.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff WITHOUT 'patients' panel -> 404
    staff_content = _create_staff_admin(db_session, 'blogs', 'content_only')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_content.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 404


# ==============================================================================
# 5. Prescription PDF Matrix
# ==============================================================================
def test_serve_prescription_pdf_rbac_matrix(client, test_patient, test_doctor, test_admin, db_session, private_files_env):
    """Matrix test: Prescription PDF serving."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date=date(2026, 12, 1),
        appointment_time=time(12, 0),
        appointment_type='video',
        status='completed',
        charges=1500.0,
        disease_category='General',
        payment_status='paid'
    )
    db_session.add(appt)
    db_session.commit()

    rx = Prescription(
        appointment_id=appt.id,
        diagnosis='Acute viral bronchitis',
        pdf_path='prescriptions/test_rx.pdf'
    )
    db_session.add(rx)
    db_session.commit()

    url = f"/files/prescription-pdf/{rx.id}"

    # Anonymous -> 404
    client.get('/auth/logout')
    assert client.get(url).status_code == 404

    # Patient owner -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 200

    # Issuing doctor -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 200

    # Unrelated doctor -> 404
    unrelated_doc_user, unrelated_doc = _create_doctor(db_session, 'OtherRx')
    with client.session_transaction() as sess:
        sess['user_id'] = unrelated_doc_user.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 404

    # Super admin -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff with 'appointments' panel -> 200
    staff_appointments = _create_staff_admin(db_session, 'appointments', 'appt_coord')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_appointments.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff WITHOUT 'appointments' panel -> 404
    staff_qa = _create_staff_admin(db_session, 'qa', 'qa_mod')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_qa.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 404


# ==============================================================================
# 6. Refund Proof Matrix
# ==============================================================================
def test_serve_refund_proof_rbac_matrix(client, test_patient, test_doctor, test_admin, db_session, private_files_env):
    """Matrix test: Refund bank transfer proof."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date=date(2026, 12, 1),
        appointment_time=time(14, 0),
        appointment_type='video',
        status='cancelled',
        charges=1500.0,
        disease_category='General',
        payment_status='paid'
    )
    db_session.add(appt)
    db_session.commit()

    refund = Refund(
        appointment_id=appt.id,
        patient_id=test_patient.patient_profile.id,
        amount=1500.0,
        reason='patient_cancelled',
        status='completed'
    )
    db_session.add(refund)
    db_session.commit()

    payout = RefundPayoutDetail(
        refund_id=refund.id,
        payment_method='easypaisa',
        account_title='Test Patient Account',
        account_number='03001234567',
        admin_proof_path='refund_proofs/test_refund_transfer.png'
    )
    db_session.add(payout)
    db_session.commit()

    url = f"/files/refund-proof/{refund.id}"

    # Anonymous -> 404
    client.get('/auth/logout')
    assert client.get(url).status_code == 404

    # Patient owner of refund -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 200

    # Doctor -> 404
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
    assert client.get(url).status_code == 404

    # Other patient -> 404
    s = get_unique_suffix()
    other_pat_user = User(
        name='Other Patient Ref', email=f'other.ref.{s}@example.com',
        phone=f'+92366{s[-7:]}', cnic=f'35201-{s[-7:]}-7',
        role='patient', is_active=True, password_hash=generate_password_hash('Password123!')
    )
    db_session.add(other_pat_user)
    db_session.commit()
    other_pat = Patient(user_id=other_pat_user.id)
    db_session.add(other_pat)
    db_session.commit()
    with client.session_transaction() as sess:
        sess['user_id'] = other_pat_user.id
        sess['user_role'] = 'patient'
    assert client.get(url).status_code == 404

    # Super admin -> 200
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff with 'accounts' panel -> 200
    staff_accounts = _create_staff_admin(db_session, 'accounts', 'accountant_ref')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_accounts.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 200

    # Staff WITHOUT 'accounts' panel -> 404
    staff_reviews = _create_staff_admin(db_session, 'reviews', 'review_mod')
    with client.session_transaction() as sess:
        sess['user_id'] = staff_reviews.id
        sess['user_role'] = 'admin'
    assert client.get(url).status_code == 404


# ==============================================================================
# 7. Direct Legacy Static URLs Blocked
# ==============================================================================
def test_legacy_static_urls_blocked(client):
    """Test legacy static URLs for private categories return 404 unconditionally."""
    assert client.get('/static/uploads/cnic/any.jpg').status_code == 404
    assert client.get('/static/uploads/degrees/any.pdf').status_code == 404
    assert client.get('/static/uploads/payment_screenshots/any.png').status_code == 404
    assert client.get('/static/uploads/medical_documents/1/any.pdf').status_code == 404
    assert client.get('/static/uploads/live_photos/any.jpg').status_code == 404
    assert client.get('/static/uploads/refund_proofs/any.png').status_code == 404
    assert client.get('/static/uploads/payout_proofs/any.png').status_code == 404
    assert client.get('/static/prescriptions/any.pdf').status_code == 404
