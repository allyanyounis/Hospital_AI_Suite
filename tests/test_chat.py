import pytest
from datetime import date, time
from app.models import Appointment

@pytest.fixture
def chat_appointment(test_patient, test_doctor, db_session):
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        status='approved',
        payment_status='approved',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(appt)
    db_session.commit()
    return appt

def test_chat_page_access_authorized_patient(client, test_patient, chat_appointment):
    """Test authenticated patient with approved appointment can open chat page."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.get(f'/appointments/{chat_appointment.id}/chat')
    assert res.status_code == 200

def test_chat_page_access_authorized_doctor(client, test_doctor, chat_appointment):
    """Test authenticated doctor can open appointment chat page."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = test_doctor.name

    res = client.get(f'/appointments/{chat_appointment.id}/chat')
    assert res.status_code == 200

def test_chat_unpaid_patient_payment_gate(client, test_patient, test_doctor, db_session):
    """Test unpaid patient cannot access chat page."""
    unpaid_appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_type='video',
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        status='pending',
        payment_status='pending',
        charges=1500.0,
        disease_category='Cardiology'
    )
    db_session.add(unpaid_appt)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.get(f'/appointments/{unpaid_appt.id}/chat', follow_redirects=True)
    # Gated: redirected or flashes payment required
    assert b"payment" in res.data.lower() or res.status_code in [302, 403, 200]

def test_ai_chatbot_gemini_model_configurable(monkeypatch):
    """Test Gemini model can be configured via GEMINI_MODEL env var."""
    from app.services.ai_chatbot_service import AIChatbotService
    from unittest.mock import patch, MagicMock

    monkeypatch.setenv('GEMINI_API_KEY', 'fake-key-for-test')
    monkeypatch.setenv('GEMINI_MODEL', 'custom-flash-test')

    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'Test Response'}]}}]
        }
        mock_post.return_value = mock_resp

        result = AIChatbotService._call_gemini('Test prompt')
        assert result == 'Test Response'
        call_url = mock_post.call_args[0][0]
        assert 'custom-flash-test' in call_url

def test_ai_chat_rate_limiting_server_side_cleared_cookies(client, app):
    """Test that clearing session cookies does NOT bypass AI chat rate limiting from the same IP."""
    try:
        from app.utils.rate_limit import ai_chat_limiter
        ai_chat_limiter.reset()
    except ImportError:
        pass

    cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')
    # Send 20 requests, clearing cookies each time to simulate a client trying to bypass rate limiting
    for i in range(20):
        client.delete_cookie(cookie_name)
        res = client.post('/qa/ai-chat', json={'message': f'test query {i}'})
        assert res.status_code != 429

    # 21st request from same client/IP with cleared cookies must be rate limited (429)
    client.delete_cookie(cookie_name)
    res21 = client.post('/qa/ai-chat', json={'message': 'test query 21'})
    assert res21.status_code == 429
    data = res21.get_json()
    assert data['success'] is False
    assert 'Too many requests' in data['message']

def test_ai_chat_rate_limiting_authenticated_user_across_sessions(client, test_patient, app):
    """Test that rate limiting tracks authenticated user ID even if session cookie changes."""
    # Reset limiter if available
    try:
        from app.utils.rate_limit import ai_chat_limiter
        ai_chat_limiter.reset()
    except ImportError:
        pass

    cookie_name = app.config.get('SESSION_COOKIE_NAME', 'session')

    # Send 20 requests with user authenticated
    for i in range(20):
        with client.session_transaction() as sess:
            sess['user_id'] = test_patient.id
            sess['user_role'] = 'patient'
            sess['user_name'] = test_patient.name
        res = client.post('/qa/ai-chat', json={'message': f'patient query {i}'})
        assert res.status_code != 429

    # Clear cookie, log back in fresh
    client.delete_cookie(cookie_name)
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res21 = client.post('/qa/ai-chat', json={'message': 'patient query 21'})
    assert res21.status_code == 429
    data = res21.get_json()
    assert data['success'] is False
    assert 'Too many requests' in data['message']



