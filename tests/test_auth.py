import pytest
from app.models import User

def test_patient_registration(client, app):
    """Test new patient registration creates user and profile."""
    payload = {
        'name': 'New Patient Test',
        'email': 'new.patient@example.com',
        'phone': '+923001112233',
        'cnic': '4210112345671',
        'password': 'Password123!',
        'password2': 'Password123!',
        'role': 'patient',
        'gender': 'male',
        'date_of_birth': '1996-06-20',
        'blood_group': 'B+',
        'allergies': 'None',
        'emergency_contact': '+923009998877',
        'emergency_relation': 'father'
    }
    res = client.post('/auth/register', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email='new.patient@example.com').first()
        assert user is not None
        assert user.role == 'patient'
        assert user.patient_profile is not None

def test_doctor_registration(client, app):
    """Test doctor registration creates unapproved doctor profile."""
    payload = {
        'name': 'Dr. Applicant Test',
        'email': 'new.doctor@example.com',
        'phone': '+923009998811',
        'cnic': '3520112345672',
        'password': 'Password123!',
        'password2': 'Password123!',
        'role': 'doctor',
        'gender': 'female',
        'date_of_birth': '1988-04-12',
        'pmc_code': 'PMC-NEW-7777',
        'specialization': 'Dermatology',
        'category': 'Dermatologist',
        'experience': '6.0',
        'education': 'MBBS, MCPS',
        'city': 'Islamabad',
        'location': 'F-8 Markaz',
        'bio': 'Experienced dermatologist.'
    }
    res = client.post('/auth/register', data=payload, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email='new.doctor@example.com').first()
        assert user is not None
        assert user.role == 'doctor'
        assert user.doctor_profile is not None
        assert user.doctor_profile.is_approved is False

def test_login_valid_credentials(client, test_patient):
    """Test login succeeds with correct credentials."""
    res = client.post('/auth/login', data={
        'email': 'patient.fixture@example.com',
        'password': 'Password123!'
    }, follow_redirects=False)
    assert res.status_code in [200, 302]
    with client.session_transaction() as sess:
        assert sess.get('user_id') == test_patient.id

def test_login_invalid_password(client, test_patient):
    """Test login fails with incorrect password."""
    res = client.post('/auth/login', data={
        'email': 'patient.fixture@example.com',
        'password': 'WrongPassword123!'
    }, follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_login_inactive_user(client, test_patient, db_session):
    """Test inactive account cannot log in."""
    test_patient.is_active = False
    db_session.commit()

    res = client.post('/auth/login', data={
        'email': 'patient.fixture@example.com',
        'password': 'Password123!'
    }, follow_redirects=True)
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_logout(client, test_patient):
    """Test logout clears session."""
    client.post('/auth/login', data={
        'email': 'patient.fixture@example.com',
        'password': 'Password123!'
    })
    res = client.get('/auth/logout', follow_redirects=True)
    assert res.status_code == 200
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_forgot_password_request(client, test_patient):
    """Test forgot password request handles registered email without errors."""
    res = client.post('/auth/forgot-password', data={
        'email': 'patient.fixture@example.com'
    }, follow_redirects=True)
    assert res.status_code == 200

def test_configurable_session_lifetime_and_cookie_security(monkeypatch):
    """Test that session lifetime is configurable via PERMANENT_SESSION_LIFETIME_DAYS and defaults to 7 days."""
    from datetime import timedelta
    from app import create_app

    # 1. Custom lifetime via env var
    monkeypatch.setenv('PERMANENT_SESSION_LIFETIME_DAYS', '14')
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'false')
    test_app = create_app('testing')
    assert test_app.config['PERMANENT_SESSION_LIFETIME'] == timedelta(days=14)
    assert test_app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert test_app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert test_app.config['SESSION_COOKIE_SECURE'] is False

    # 2. Default lifetime (7 days) when env var unset
    monkeypatch.delenv('PERMANENT_SESSION_LIFETIME_DAYS', raising=False)
    test_app_default = create_app('testing')
    assert test_app_default.config['PERMANENT_SESSION_LIFETIME'] == timedelta(days=7)

    # 3. Secure cookies when SESSION_COOKIE_SECURE is enabled or HTTPS scheme preferred
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'true')
    test_app_secure = create_app('testing')
    assert test_app_secure.config['SESSION_COOKIE_SECURE'] is True



def test_password_complexity_validator():
    """Unit test for check_password_complexity verifying all 5 requirements."""
    from app.utils.auth import check_password_complexity

    # Short (<8)
    ok, errs = check_password_complexity("Pass1!")
    assert not ok and any("at least 8 characters" in e for e in errs)

    # Missing uppercase
    ok, errs = check_password_complexity("password123!")
    assert not ok and any("uppercase" in e for e in errs)

    # Missing lowercase
    ok, errs = check_password_complexity("PASSWORD123!")
    assert not ok and any("lowercase" in e for e in errs)

    # Missing number
    ok, errs = check_password_complexity("Password!")
    assert not ok and any("number" in e for e in errs)

    # Missing special char
    ok, errs = check_password_complexity("Password123")
    assert not ok and any("special character" in e for e in errs)

    # Valid
    ok, errs = check_password_complexity("Password123!")
    assert ok and len(errs) == 0


def test_registration_rejects_weak_passwords(client, app):
    """Integration test: Registration form rejects weak passwords with validation error."""
    payload = {
        'name': 'Weak Password Patient',
        'email': 'weak.pass.patient@example.com',
        'phone': '+923001112239',
        'cnic': '4210112345679',
        'password': 'weakpassword',
        'password2': 'weakpassword',
        'role': 'patient',
        'gender': 'male',
        'date_of_birth': '1996-06-20',
        'blood_group': 'B+'
    }
    res = client.post('/auth/register', data=payload)
    # Registration should fail and re-render form with error
    html = res.get_data(as_text=True)
    assert "Password must" in html or res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email='weak.pass.patient@example.com').first()
        assert user is None, "User with weak password must NOT be created in database!"


def test_password_reset_rejects_weak_passwords(client, test_patient, db_session):
    """Integration test: Password reset endpoint rejects weak passwords."""
    from datetime import datetime, timedelta
    test_patient.reset_token = "valid-test-reset-token-1234"
    test_patient.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db_session.commit()

    # Try weak password
    res = client.post('/auth/reset-password/valid-test-reset-token-1234', data={
        'password': 'weakpassword',
        'confirm_password': 'weakpassword'
    }, follow_redirects=True)
    html = res.get_data(as_text=True)
    assert "Password must contain" in html

    # Try strong password
    res_good = client.post('/auth/reset-password/valid-test-reset-token-1234', data={
        'password': 'NewStrongPassword123!',
        'confirm_password': 'NewStrongPassword123!'
    }, follow_redirects=True)
    assert res_good.status_code == 200
    assert test_patient.check_password('NewStrongPassword123!')
