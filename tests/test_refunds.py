import pytest
from datetime import date, time, datetime, timedelta
from app.models import Appointment, Refund

def test_patient_cancellation_request_allowed_more_than_3h(client, test_patient, test_doctor, db_session, app):
    """Test patient can request cancellation when appointment is > 3 hours away."""
    future_date = date.today() + timedelta(days=2)
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=future_date,
        appointment_time=time(14, 0),
        status='approved',
        payment_status='approved',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.post(f'/patients/appointments/{appt_id}/cancel', data={
        'reason': 'Scheduling conflict'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.cancellation_requested is True

def test_patient_cancellation_blocked_less_than_3h(client, test_patient, test_doctor, db_session, app):
    """Test cancellation request is rejected if less than 3 hours before appointment."""
    today = date.today()
    near_time = (datetime.now() + timedelta(minutes=30)).time()
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=today,
        appointment_time=near_time,
        status='approved',
        payment_status='approved',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.post(f'/patients/appointments/{appt_id}/cancel', data={
        'reason': 'Last minute change'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.cancellation_requested is not True

def test_doctor_approves_cancellation(client, test_doctor, test_patient, db_session, app):
    """Test doctor approves patient cancellation request."""
    future_date = date.today() + timedelta(days=2)
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=future_date,
        appointment_time=time(14, 0),
        status='approved',
        payment_status='approved',
        cancellation_requested=True,
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

    res = client.post(f'/doctors/cancellation/{appt_id}/approve', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.status == 'cancelled'
        assert updated.cancellation_approved is True

from unittest.mock import patch

def test_cancellation_window_clock_patched_under_3h(client, test_patient, test_doctor, db_session, app):
    """Test 3h window strictly rejects when patched PKT time is 2 hours before appointment."""
    appt_dt = datetime(2026, 12, 1, 14, 0)
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=appt_dt.date(),
        appointment_time=appt_dt.time(),
        status='approved',
        payment_status='approved',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    with patch('app.routes.patients.pkt_now_naive', return_value=datetime(2026, 12, 1, 12, 0)):
        res = client.post(f'/patients/appointments/{appt_id}/cancel', data={'reason': 'Late cancel'}, follow_redirects=True)
        assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.cancellation_requested is not True

def test_cancellation_window_clock_patched_over_3h(client, test_patient, test_doctor, db_session, app):
    """Test 3h window allows cancellation when patched PKT time is 4 hours before appointment."""
    appt_dt = datetime(2026, 12, 1, 14, 0)
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=appt_dt.date(),
        appointment_time=appt_dt.time(),
        status='approved',
        payment_status='approved',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    appt_id = appt.id

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    with patch('app.routes.patients.pkt_now_naive', return_value=datetime(2026, 12, 1, 10, 0)):
        res = client.post(f'/patients/appointments/{appt_id}/cancel', data={'reason': 'Timely cancel'}, follow_redirects=True)
        assert res.status_code == 200

    with app.app_context():
        updated = Appointment.query.get(appt_id)
        assert updated.cancellation_requested is True
