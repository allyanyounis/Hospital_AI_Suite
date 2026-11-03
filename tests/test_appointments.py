import pytest
from datetime import date, timedelta
from app import db
from app.models import Appointment

def test_booking_creation(client, test_patient, test_doctor, app):
    """Test authenticated patient can create an appointment."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    target_dt = date.today() + timedelta(days=2)
    target_date = target_dt.strftime('%Y-%m-%d')
    doc_id = test_doctor.doctor_profile.id

    payload = {
        'appointment_type': 'video',
        'appointment_date': target_date,
        'appointment_time': '10:00',
        'reason_for_visit': 'General cardiac follow-up.',
        'practice': 'Video Consultation'
    }

    res = client.post(f'/patients/doctor/{doc_id}/book?type=video&practice=Video%20Consultation', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        appt = Appointment.query.filter_by(patient_id=test_patient.patient_profile.id, appointment_date=target_dt).order_by(Appointment.id.desc()).first()
        assert appt is not None
        assert appt.status == 'pending'
        assert appt.payment_status == 'pending'
        assert appt.charges == 1500.0
        # Cleanup
        db.session.delete(appt)
        db.session.commit()

def test_booking_unapproved_doctor_rejected(client, test_patient, test_doctor, db_session):
    """Test booking an unapproved doctor is rejected."""
    test_doctor.doctor_profile.is_approved = False
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    doc_id = test_doctor.doctor_profile.id
    try:
        res = client.get(f'/patients/doctor/{doc_id}/book', follow_redirects=True)
        assert res.status_code == 200
        assert b"not approved yet" in res.data or b"warning" in res.data
    finally:
        test_doctor.doctor_profile.is_approved = True
        db_session.commit()

def test_admin_payment_approval_and_commission_split(client, test_patient, test_doctor, test_admin, app, db_session):
    """Test admin payment approval updates status and completion credits 80/20 commission split."""
    from datetime import date, time
    from app.models import Appointment
    from app.services.accounts_service import credit_doctor_after_completion

    # Create pending appointment
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today() + timedelta(days=2),
        appointment_time=time(10, 0),
        status='pending',
        payment_status='submitted',
        charges=2000.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    # Admin session
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'
        sess['user_name'] = test_admin.name

    res = client.post(f'/admin/payments/{appt_id}/approve', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.payment_status == 'approved'
        
        # Test accounts service credit on completion
        updated.status = 'completed'
        credit_doctor_after_completion(updated)
        assert updated.platform_commission_percent == 20
        assert updated.platform_commission_amount == 400.0

from unittest.mock import patch

def test_cleanup_expired_payments_reuses_app_context_perf_02(app, db_session):
    """Test ISS-PERF-02: cleanup_expired_payments reuses current_app instead of calling create_app()."""
    from app.utils.cleanup_expired_payments import cleanup_expired_payments
    with app.app_context():
        with patch('app.utils.cleanup_expired_payments.create_app') as mock_create_app:
            cleanup_expired_payments()
            mock_create_app.assert_not_called()

def test_booking_same_day_slot_in_past_rejected(client, test_patient, test_doctor, app):
    """Test same-day slot in the past is rejected."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    doc_id = test_doctor.doctor_profile.id
    target_date = '2026-12-15'
    payload = {
        'appointment_type': 'video',
        'appointment_date': target_date,
        'appointment_time': '10:00',
        'reason_for_visit': 'Routine checkup.',
        'practice': 'Video Consultation'
    }

    from app.utils.timezone import PAKISTAN_TZ
    from datetime import datetime
    fake_now = PAKISTAN_TZ.localize(datetime(2026, 12, 15, 14, 0))

    with patch('app.routes.patients.get_pakistan_now', return_value=fake_now):
        res = client.post(f'/patients/doctor/{doc_id}/book?type=video&practice=Video%20Consultation', data=payload, follow_redirects=True)
        assert b"passed" in res.data.lower()

    with app.app_context():
        appt = Appointment.query.filter_by(patient_id=test_patient.patient_profile.id, appointment_date=date(2026, 12, 15)).first()
        assert appt is None

def test_booking_same_day_slot_in_future_allowed(client, test_patient, test_doctor, app):
    """Test same-day slot in the future is allowed."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    doc_id = test_doctor.doctor_profile.id
    target_date = '2026-12-16'
    payload = {
        'appointment_type': 'video',
        'appointment_date': target_date,
        'appointment_time': '15:00',
        'reason_for_visit': 'Routine checkup.',
        'practice': 'Video Consultation'
    }

    from app.utils.timezone import PAKISTAN_TZ
    from datetime import datetime
    fake_now = PAKISTAN_TZ.localize(datetime(2026, 12, 16, 10, 0))

    with patch('app.routes.patients.get_pakistan_now', return_value=fake_now):
        res = client.post(f'/patients/doctor/{doc_id}/book?type=video&practice=Video%20Consultation', data=payload, follow_redirects=True)
        assert res.status_code == 200

    with app.app_context():
        appt = Appointment.query.filter_by(patient_id=test_patient.patient_profile.id, appointment_date=date(2026, 12, 16)).first()
        assert appt is not None
        assert appt.appointment_time == datetime.strptime('15:00', '%H:%M').time()
        # Cleanup
        db.session.delete(appt)
        db.session.commit()

def test_booking_pkt_date_boundary_skew(client, test_patient, test_doctor, app):
    """Test 23:50 PKT when system date differs from PKT date."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    doc_id = test_doctor.doctor_profile.id
    
    from app.utils.timezone import PAKISTAN_TZ
    from datetime import datetime
    fake_now = PAKISTAN_TZ.localize(datetime(2026, 12, 4, 1, 0))

    # User attempts to book 2026-12-03 (yesterday in PKT, even if system date was 2026-12-03)
    payload_past = {
        'appointment_type': 'video',
        'appointment_date': '2026-12-03',
        'appointment_time': '10:00',
        'reason_for_visit': 'Late night booking.',
        'practice': 'Video Consultation'
    }

    with patch('app.routes.patients.get_pakistan_now', return_value=fake_now):
        res = client.post(f'/patients/doctor/{doc_id}/book?type=video&practice=Video%20Consultation', data=payload_past, follow_redirects=True)
        assert b"past" in res.data.lower()

    with app.app_context():
        appt = Appointment.query.filter_by(patient_id=test_patient.patient_profile.id, appointment_date=date(2026, 12, 3)).first()
        assert appt is None
