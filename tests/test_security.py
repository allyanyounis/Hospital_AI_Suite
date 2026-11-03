import pytest
from app.models import Admin, User

def test_csrf_protection_enforced(app, client):
    """ISS-SEC-01: State-changing POST without CSRF token must return 400."""
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        res = client.post('/newsletter', data={'email': 'attacker@example.com'})
        assert res.status_code == 400
        assert res.get_json().get('error') == 'csrf'
    finally:
        app.config['WTF_CSRF_ENABLED'] = False

def test_static_upload_access_control(client):
    """ISS-SEC-03: Sensitive and unclassified uploads must return 404 via static endpoint."""
    res = client.get('/static/uploads/0595c87e7dff47e09a849a21570fa5ba.png')
    assert res.status_code in [401, 403, 404]

def test_admin_staff_rbac_ajax_403(client, test_admin, db_session):
    """Test restricted staff admin receives 403 on forbidden panels via AJAX."""
    from werkzeug.security import generate_password_hash
    from app.models import Admin

    # Create or reuse restricted staff member
    staff_user = User.query.filter_by(email='support.test@quickcare.pk').first()
    if not staff_user:
        staff_user = User(
            name='Support Staff Member',
            email='support.test@quickcare.pk',
            phone='+923001239999',
            cnic='3520212345678',
            role='admin',
            is_active=True,
            password_hash=generate_password_hash('Password123!')
        )
        db_session.add(staff_user)
        db_session.commit()

    admin_profile = Admin.query.filter_by(user_id=staff_user.id).first()
    if not admin_profile:
        admin_profile = Admin(
            user_id=staff_user.id,
            admin_level='staff',
            staff_role='patient_support_manager'
        )
        db_session.add(admin_profile)
        db_session.commit()

    try:
        with client.session_transaction() as sess:
            sess['user_id'] = staff_user.id
            sess['user_role'] = 'admin'
            sess['user_name'] = staff_user.name

        # patient_support_manager does not have access to accounts panel
        res = client.get('/admin/accounts', headers={'X-Requested-With': 'XMLHttpRequest'})
        assert res.status_code == 403
        assert b"Permission denied" in res.data or b"error" in res.data
    finally:
        db_session.delete(staff_user)
        db_session.commit()

def test_video_token_missing_credentials_clean_error(client, test_patient, test_doctor, db_session, app):
    """Test ISS-SEC-02: Missing Agora credentials returns a clean 503 error instead of 500."""
    from datetime import datetime, timedelta
    from app.models import Appointment

    appt_dt = datetime.now() + timedelta(minutes=15)
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

    app.config['AGORA_APP_ID'] = ''
    app.config['AGORA_APP_CERTIFICATE'] = ''

    res = client.get(f'/video/token/{appt_id}')
    assert res.status_code == 503
    data = res.get_json()
    assert data is not None
    assert 'not configured' in data.get('error', '').lower()

