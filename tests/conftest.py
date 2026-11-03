import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Explicitly load .env to guarantee TEST_DATABASE_URL is always populated
load_dotenv(os.path.join(project_root, '.env'))

TEST_DB_PATH = os.path.join(project_root, 'tests', 'test_exec.db')

os.environ['FLASK_ENV'] = 'testing'
os.environ['ENABLE_EMAILS'] = 'false'
os.environ['AGORA_ENABLE_RECORDING'] = 'false'

@pytest.fixture(scope='session', autouse=True)
def mock_external_services():
    """Mock external third-party services globally for all tests."""
    with patch('app.scheduler.init_scheduler'), \
         patch('app.routes.video.RtcTokenBuilder.buildTokenWithUid', return_value='mocked-agora-token'), \
         patch('app.services.recording_service.maybe_start_recording', return_value=True), \
         patch('app.services.recording_service.stop_recording', return_value=True), \
         patch('app.services.ai_chatbot_service.AIChatbotService.answer', return_value={'response': 'Mocked AI consultation guidance', 'llm_provider': 'mock'}), \
         patch('app.services.email_service.send_email', return_value=True), \
         patch('app.services.email_service.send_welcome_patient_email', return_value=True), \
         patch('app.services.email_service.send_welcome_doctor_email', return_value=True):
        yield

@pytest.fixture(scope='session')
def app():
    """Create and configure a fresh Flask app instance for testing."""
    from config import normalize_db_url
    from app import create_app, db

    test_db_uri = os.environ.get('APP_TEST_DATABASE_URL')
    if not test_db_uri:
        raw_test_url = os.environ.get('TEST_DATABASE_URL')
        if raw_test_url and 'postgres' in raw_test_url:
            from urllib.parse import urlparse, quote_plus
            u = urlparse(raw_test_url)
            app_pass = quote_plus(os.environ.get('ARAMIS_APP_PASSWORD', 'AramisApp2026!Sec#'))
            netloc = f"aramis_app:{app_pass}@{u.hostname}"
            if u.port:
                netloc += f":{u.port}"
            test_db_uri = u._replace(netloc=netloc).geturl()
        else:
            test_db_uri = raw_test_url

    test_db_uri = normalize_db_url(test_db_uri)
    is_postgres = bool(test_db_uri and 'postgres' in test_db_uri)

    if not is_postgres and os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    if not is_postgres:
        test_db_uri = f'sqlite:///{TEST_DB_PATH}'

    flask_app = create_app('testing')
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_db_uri,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost'
    })

    with flask_app.app_context():
        # Prove tests run on PostgreSQL with pgvector
        from sqlalchemy import text
        print(f"\n[TEST_DB_VERIFY] Dialect: {db.engine.dialect.name} | URL: {db.engine.url}")
        assert db.engine.dialect.name == 'postgresql', f"Tests must run on PostgreSQL, but got {db.engine.dialect.name}"
        ext = db.session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
        print(f"[TEST_DB_VERIFY] Vector extension detected: {ext}")
        assert ext == 'vector', "pgvector extension must be active on PostgreSQL test database"

        if is_postgres:
            from app.models import Hospital
            h1 = Hospital.query.filter_by(id=1).first()
            if not h1:
                h1 = Hospital(id=1, name="Aramis Demo Hospital", slug="aramis-demo", city="Lahore", address="12-A Medical Enclave, Jail Road, Lahore", status="active")
                db.session.add(h1)
                db.session.commit()
            yield flask_app
            db.session.remove()
        else:
            db.drop_all()
            db.create_all()
            yield flask_app
            db.session.remove()
            db.drop_all()

    if not is_postgres and os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """Direct database session with automatic transaction cleanup."""
    from app import db
    yield db.session
    db.session.rollback()

@pytest.fixture
def test_patient(app, db_session):
    """Create a verified test patient user."""
    from app.models import User, Patient
    from werkzeug.security import generate_password_hash
    from datetime import date

    existing = User.query.filter_by(email='patient.fixture@example.com').first()
    if existing:
        if not existing.patient_profile:
            db_session.delete(existing)
            db_session.commit()
        else:
            existing.password_hash = generate_password_hash('Password123!')
            existing.is_active = True
            db_session.commit()
            return existing

    user = User(
        name='Test Patient',
        email='patient.fixture@example.com',
        phone='+923001234567',
        cnic='0000000000000',
        role='patient',
        gender='male',
        date_of_birth=date(1995, 5, 15),
        is_active=True,
        password_hash=generate_password_hash('Password123!')
    )
    db_session.add(user)
    db_session.commit()

    patient = Patient(
        user_id=user.id,
        blood_group='A+',
        emergency_contact='+923009999999',
        emergency_relation='father'
    )
    db_session.add(patient)
    db_session.commit()
    return user

@pytest.fixture
def test_doctor(app, db_session):
    """Create an approved and verified test doctor user."""
    import json
    from app.models import User, Doctor
    from werkzeug.security import generate_password_hash
    from datetime import date

    existing = User.query.filter_by(email='doctor.fixture@example.com').first()
    if existing:
        if not existing.doctor_profile:
            db_session.delete(existing)
            db_session.commit()
        else:
            existing.password_hash = generate_password_hash('Password123!')
            existing.is_active = True
            existing.doctor_profile.is_approved = True
            existing.doctor_profile.is_verified = True
            from app.models import HospitalMembership
            memb = HospitalMembership.query.filter_by(user_id=existing.id, hospital_id=1).first()
            if not memb:
                memb = HospitalMembership(user_id=existing.id, hospital_id=1, role='doctor', status='active')
                db_session.add(memb)
            db_session.commit()
            return existing

    user = User(
        name='Dr. Test Fixture',
        email='doctor.fixture@example.com',
        phone='+923007654321',
        cnic='1111111111111',
        role='doctor',
        gender='female',
        date_of_birth=date(1985, 8, 20),
        is_active=True,
        password_hash=generate_password_hash('Password123!')
    )
    db_session.add(user)
    db_session.commit()

    slots = {
        "monday": {"start_time": "10:00", "end_time": "17:00", "duration": 30, "hospital": "Video Consultation", "location": "Online", "video_price": 1500.0, "physical_price": 2000.0},
        "tuesday": {"start_time": "10:00", "end_time": "17:00", "duration": 30, "hospital": "Video Consultation", "location": "Online", "video_price": 1500.0, "physical_price": 2000.0},
        "wednesday": {"start_time": "10:00", "end_time": "17:00", "duration": 30, "hospital": "Video Consultation", "location": "Online", "video_price": 1500.0, "physical_price": 2000.0},
        "thursday": {"start_time": "10:00", "end_time": "17:00", "duration": 30, "hospital": "Video Consultation", "location": "Online", "video_price": 1500.0, "physical_price": 2000.0},
        "friday": {"start_time": "10:00", "end_time": "17:00", "duration": 30, "hospital": "Video Consultation", "location": "Online", "video_price": 1500.0, "physical_price": 2000.0}
    }

    doctor = Doctor(
        user_id=user.id,
        hospital_id=1,
        pmc_code='PMC-FIXTURE-1111',
        specialization='Cardiology',
        category='Cardiologist',
        experience=5.0,
        education='MBBS, FCPS Cardiology',
        bio='Specialist in clinical cardiology with clinical trial experience.',
        city='Lahore',
        location='Gulberg III',
        is_approved=True,
        is_verified=True,
        time_slots=slots
    )
    db_session.add(doctor)
    db_session.flush()
    from app.models import HospitalMembership
    memb = HospitalMembership.query.filter_by(user_id=user.id, hospital_id=1).first()
    if not memb:
        memb = HospitalMembership(user_id=user.id, hospital_id=1, role='doctor', status='active')
        db_session.add(memb)
    db_session.commit()
    return user

@pytest.fixture
def test_admin(app, db_session):
    """Create a super-admin user."""
    from app.models import User, Admin
    from werkzeug.security import generate_password_hash

    existing = User.query.filter_by(email='admin.fixture@quickcare.pk').first()
    if existing:
        existing.password_hash = generate_password_hash('Admin123!')
        existing.is_active = True
        from app.models import HospitalMembership
        memb = HospitalMembership.query.filter_by(user_id=existing.id, hospital_id=1).first()
        if not memb:
            memb = HospitalMembership(user_id=existing.id, hospital_id=1, role='hospital_admin', status='active')
            db_session.add(memb)
        db_session.commit()
        return existing

    user = User(
        name='Super Admin Fixture',
        email='admin.fixture@quickcare.pk',
        phone='+923000000000',
        cnic='9999999999999',
        role='admin',
        is_active=True,
        password_hash=generate_password_hash('Admin123!')
    )
    db_session.add(user)
    db_session.commit()

    admin = Admin(
        user_id=user.id,
        admin_level='super'
    )
    db_session.add(admin)
    db_session.flush()
    from app.models import HospitalMembership
    memb = HospitalMembership.query.filter_by(user_id=user.id, hospital_id=1).first()
    if not memb:
        memb = HospitalMembership(user_id=user.id, hospital_id=1, role='hospital_admin', status='active')
        db_session.add(memb)
    db_session.commit()
    return user
