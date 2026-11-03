import pytest
import re
from flask_wtf.csrf import generate_csrf
from app.models import Appointment
from datetime import date, time


@pytest.fixture
def enable_csrf(app):
    """Context fixture to enable CSRF enforcement for tests."""
    from flask import g
    g.pop('csrf_token', None)
    app.config['WTF_CSRF_ENABLED'] = True
    yield
    g.pop('csrf_token', None)
    app.config['WTF_CSRF_ENABLED'] = False


def _get_csrf_token(client):
    """Helper to extract a valid CSRF token from the session/page."""
    from flask import g
    g.pop('csrf_token', None)
    res = client.get('/auth/login')
    html = res.get_data(as_text=True)
    match_meta = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if match_meta:
        return match_meta.group(1)
    match_input = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if match_input:
        return match_input.group(1)
    return None


def test_post_without_token_rejected_json_400(app, client, enable_csrf):
    """State-changing POST without CSRF token returns 400 Bad Request."""
    res = client.post('/newsletter', data={'email': 'attacker@example.com'})
    assert res.status_code == 400
    data = res.get_json()
    assert data is not None
    assert data.get('error') == 'csrf'


def test_post_with_valid_token_in_form(app, client, enable_csrf):
    """State-changing POST with valid CSRF token in form data succeeds."""
    with client:
        token = _get_csrf_token(client)
        res = client.post('/newsletter', data={'email': 'valid@example.com', 'csrf_token': token})
        assert res.status_code in [200, 302]


def test_post_with_valid_token_in_header(app, client, enable_csrf):
    """State-changing POST with X-CSRFToken header succeeds."""
    with client:
        token = _get_csrf_token(client)
        res = client.post('/newsletter', data={'email': 'valid.header@example.com'}, headers={'X-CSRFToken': token})
        assert res.status_code in [200, 302]


def test_browser_form_submission_expired_redirects(app, client, enable_csrf):
    """Browser form submission without token flashes friendly message and redirects back."""
    res = client.post(
        '/newsletter',
        data={'email': 'browser@example.com'},
        headers={
            'Accept': 'text/html,application/xhtml+xml',
            'Referer': 'http://localhost/newsletter-page'
        }
    )
    assert res.status_code == 302
    assert res.headers['Location'] == 'http://localhost/newsletter-page'

    # Follow redirect and verify flash message
    follow_res = client.get(res.headers['Location'])
    assert b'Your session expired, please try again.' in follow_res.data


def test_ajax_endpoint_missing_token_returns_json_400(app, client, enable_csrf):
    """AJAX request without CSRF token returns JSON 400 error."""
    res = client.post(
        '/appointments/api/send-message',
        json={'appointment_id': 1, 'message': 'Hello'},
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data.get('error') == 'csrf'


def test_safepay_webhook_exempt_from_csrf(app, client, enable_csrf):
    """Safepay server-side webhook is exempted from CSRF protection."""
    # Webhook receives JSON without CSRF token
    res = client.post('/safepay/webhook', json={'tracker_token': 'dummy_safepay_tracker'})
    # The response should NOT be 400 with {'error': 'csrf'}
    # It proceeds to application handler (which returns 404 or success depending on appointment existence)
    if res.status_code == 400 and res.is_json:
        assert res.get_json().get('error') != 'csrf'
    assert res.status_code in [200, 404]
