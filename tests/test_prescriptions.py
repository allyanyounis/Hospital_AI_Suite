import pytest
from datetime import date, time
from app.models import Appointment, Prescription

@pytest.fixture
def sample_appointment(test_patient, test_doctor, db_session):
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        status='approved',
        payment_status='approved',
        prescription_unlocked=True,
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    return appt

def test_doctor_creates_prescription(client, test_doctor, sample_appointment, app):
    """Test doctor can create digital prescription with medicines."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    payload = {
        'weight': '70',
        'bp': '120/80',
        'temp': '98.6',
        'pulse': '72',
        'diagnosis': 'Seasonal Allergic Rhinitis',
        'complaints': 'Sneezing and runny nose for 3 days',
        'advice': 'Avoid dust, stay hydrated',
        'medicine_name[]': ['Cetirizine 10mg'],
        'medicine_dosage[]': ['10mg'],
        'medicine_frequency[]': ['Once Daily'],
        'medicine_duration[]': ['7 Days'],
        'medicine_instructions[]': ['Take at bedtime']
    }
    res = client.post(f'/prescriptions/create/{sample_appointment.id}', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        rx = Prescription.query.filter_by(appointment_id=sample_appointment.id).first()
        assert rx is not None
        assert rx.diagnosis == 'Seasonal Allergic Rhinitis'
        assert len(rx.medicines) == 1

def test_patient_views_prescription(client, test_patient, test_doctor, sample_appointment, db_session):
    """Test authenticated patient can view prescription."""
    rx = Prescription(
        appointment_id=sample_appointment.id,
        diagnosis='Acute Pharyngitis',
        advice='Warm water gargles'
    )
    db_session.add(rx)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.get(f'/prescriptions/view/{rx.id}')
    assert res.status_code == 200
    assert b"Acute Pharyngitis" in res.data

def test_unauthenticated_prescription_view_redirects(client, sample_appointment, db_session):
    """Test unauthenticated access to view_prescription redirects to login instead of crashing."""
    rx = Prescription(
        appointment_id=sample_appointment.id,
        diagnosis='Acute Bronchitis'
    )
    db_session.add(rx)
    db_session.commit()

    res = client.get(f'/prescriptions/view/{rx.id}')
    assert res.status_code == 302
    assert '/auth/login' in res.headers.get('Location', '')

def test_unauthenticated_prescription_download_redirects(client, sample_appointment, db_session):
    """Test unauthenticated access to download_prescription redirects to login instead of crashing."""
    rx = Prescription(
        appointment_id=sample_appointment.id,
        diagnosis='Acute Bronchitis Download'
    )
    db_session.add(rx)
    db_session.commit()

    res = client.get(f'/prescriptions/download/{rx.id}')
    assert res.status_code == 302
    assert '/auth/login' in res.headers.get('Location', '')

def test_authenticated_prescription_pdf_download(client, test_patient, sample_appointment, db_session):
    """Test authenticated PDF download works using xhtml2pdf."""
    rx = Prescription(
        appointment_id=sample_appointment.id,
        diagnosis='Normal Checkup'
    )
    db_session.add(rx)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.get(f'/prescriptions/download/{rx.id}')
    assert res.status_code == 200
    assert res.headers.get('content-type', '').startswith('application/pdf')
    assert len(res.data) > 1000

def _valid_rx_payload(diagnosis='Test Diagnosis'):
    return {
        'diagnosis': diagnosis,
        'medicine_name[]': ['Cetirizine 10mg'],
        'medicine_dosage[]': ['10mg'],
        'medicine_frequency[]': ['Once Daily'],
        'medicine_duration[]': ['7 Days'],
        'medicine_instructions[]': ['Take at bedtime']
    }

def test_prescription_create_unpaid_blocked(client, test_doctor, test_patient, db_session, app):
    """Test unpaid appointment is blocked from prescription creation."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(11, 0),
        status='approved',
        payment_status='pending',
        prescription_unlocked=False,
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    payload = _valid_rx_payload('Test Block Unpaid')
    res = client.post(f'/prescriptions/create/{appt_id}', data=payload, follow_redirects=False)
    assert res.status_code == 302
    assert '/doctors/appointments' in res.headers.get('Location', '')

    with app.app_context():
        assert Prescription.query.filter_by(appointment_id=appt_id).first() is None

def test_prescription_create_video_without_unlock_blocked(client, test_doctor, test_patient, db_session, app):
    """Test video appointment without 3-minute video unlock is blocked and redirected to consultation."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(12, 0),
        status='approved',
        payment_status='approved',
        prescription_unlocked=False,
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    payload = _valid_rx_payload('Test Block Locked Video')
    res = client.post(f'/prescriptions/create/{appt_id}', data=payload, follow_redirects=False)
    assert res.status_code == 302
    assert f'/appointments/{appt_id}' in res.headers.get('Location', '')

    with app.app_context():
        assert Prescription.query.filter_by(appointment_id=appt_id).first() is None

def test_prescription_create_video_with_unlock_allowed(client, test_doctor, test_patient, db_session, app):
    """Test video appointment with prescription_unlocked=True is allowed."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(13, 0),
        status='approved',
        payment_status='approved',
        prescription_unlocked=True,
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    payload = _valid_rx_payload('Allowed Video Consultation')
    res = client.post(f'/prescriptions/create/{appt_id}', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        rx = Prescription.query.filter_by(appointment_id=appt_id).first()
        assert rx is not None
        assert rx.diagnosis == 'Allowed Video Consultation'

def test_prescription_create_physical_paid_and_approved_allowed(client, test_doctor, test_patient, db_session, app):
    """Test physical in-clinic appointment bypasses video consultation unlock requirement."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='physical',
        appointment_date=date.today(),
        appointment_time=time(14, 0),
        status='approved',
        payment_status='approved',
        prescription_unlocked=False,
        charges=2000.0,
        disease_category='General'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    payload = _valid_rx_payload('Physical In-Clinic Prescription')
    res = client.post(f'/prescriptions/create/{appt_id}', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        rx = Prescription.query.filter_by(appointment_id=appt_id).first()
        assert rx is not None
        assert rx.diagnosis == 'Physical In-Clinic Prescription'

def test_prescription_create_different_doctor_blocked(client, test_patient, test_doctor, db_session, app):
    """Test doctor cannot create prescription for another doctor's appointment."""
    from app.models import User, Doctor
    from werkzeug.security import generate_password_hash

    # Create or reuse second doctor
    other_user = User.query.filter_by(email='other.doctor@example.com').first()
    if not other_user:
        other_user = User(
            name='Dr. Other Doctor',
            email='other.doctor@example.com',
            phone='+923009876543',
            cnic='2222222222222',
            role='doctor',
            gender='male',
            date_of_birth=date(1980, 1, 1),
            is_active=True,
            password_hash=generate_password_hash('Password123!')
        )
        db_session.add(other_user)
        db_session.commit()

    other_doc = Doctor.query.filter_by(user_id=other_user.id).first()
    if not other_doc:
        other_doc = Doctor(
            user_id=other_user.id,
            hospital_id=1,
            pmc_code='PMC-OTHER-2222',
            specialization='Pediatrics',
            category='Pediatrician',
            experience=10.0,
            education='MBBS, FCPS',
            bio='Experienced pediatrician bio',
            city='Lahore',
            location='Gulberg'
        )
        db_session.add(other_doc)
        db_session.commit()

    # Appointment belongs to test_doctor
    appt = Appointment(
        hospital_id=1,
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='physical',
        appointment_date=date.today(),
        appointment_time=time(15, 0),
        status='approved',
        payment_status='approved',
        prescription_unlocked=False,
        charges=2000.0,
        disease_category='General'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    try:
        # Log in as other doctor
        with client.session_transaction() as sess:
            sess['user_id'] = other_user.id
            sess['user_role'] = 'doctor'
            sess['user_name'] = other_user.name

        payload = _valid_rx_payload('Intruder Prescription')
        res = client.post(f'/prescriptions/create/{appt_id}', data=payload, follow_redirects=False)
        assert res.status_code == 302
        assert '/doctors/appointments' in res.headers.get('Location', '')

        with app.app_context():
            assert Prescription.query.filter_by(appointment_id=appt_id).first() is None
    finally:
        db_session.delete(appt)
        db_session.delete(other_user)
        db_session.commit()

