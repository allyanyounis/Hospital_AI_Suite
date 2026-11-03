"""
tests/test_safepay.py
Unit and integration tests for Safepay payment gateway:
- Unit conversion helper (to_safepay_amount, from_safepay_amount)
- Correct checkout request amount (Rs. 2,500.00, not 250,000)
- Verification amount and currency validation
- Webhook approval on matching amount and rejection on mismatched amount
"""

import pytest
from unittest.mock import patch, MagicMock
from app.models import Appointment
from app.services.safepay_service import (
    to_safepay_amount,
    from_safepay_amount,
    verify_safepay_order,
)


def test_safepay_amount_helpers():
    """Verify conversion helpers produce major units and handle edge cases."""
    assert to_safepay_amount(2500) == 2500.0
    assert to_safepay_amount(2500.0) == 2500.0
    assert to_safepay_amount("2500") == 2500.0
    assert to_safepay_amount(1500.50) == 1500.50

    assert from_safepay_amount(2500) == 2500.0
    assert from_safepay_amount(2500.0) == 2500.0
    assert from_safepay_amount({'amount': 2500, 'currency': 'PKR'}) == 2500.0
    assert from_safepay_amount({'amount': 1800.75}) == 1800.75


def test_safepay_checkout_sends_exact_rupees_2500(client, test_patient, test_doctor, db_session):
    """A Rs. 2,500 consultation must send 2500.0 (NOT 250000) to Safepay Order API."""
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date='2026-11-20',
        appointment_time='11:00:00',
        status='pending',
        payment_status='pending',
        charges=2500.0,
        disease_category='Cardiology',
        appointment_type='online'
    )
    db_session.add(appt)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'token': 'track_test_checkout_2500',
            'amount': 2500.0,
            'currency': 'PKR',
            'state': 'TRACKER_STARTED'
        }
    }

    with patch('requests.post', return_value=mock_resp) as mock_post:
        res = client.get(f'/safepay/checkout/{appt.id}')
        assert res.status_code == 302
        assert 'checkout/pay' in res.headers.get('Location', '')
        assert 'beacon=track_test_checkout_2500' in res.headers.get('Location', '')

        # Verify the payload sent to Safepay
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs.get('json', {})
        assert payload.get('amount') == 2500.0, f"Expected 2500.0 but got {payload.get('amount')}"
        assert payload.get('currency') == 'PKR'

    # Cleanup
    db_session.delete(appt)
    db_session.commit()


def test_safepay_verify_accepts_matching_amount(app):
    """Verification succeeds when state is TRACKER_ENDED and amount equals charges."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'state': 'TRACKER_ENDED',
            'amount': 2500.0,
            'currency': 'PKR'
        }
    }

    with app.app_context(), patch('requests.get', return_value=mock_resp):
        is_valid, reason, data = verify_safepay_order('track_good', expected_charges=2500.0, expected_currency='PKR')
        assert is_valid is True
        assert 'successfully' in reason.lower()
        assert data.get('amount') == 2500.0


def test_safepay_verify_rejects_mismatched_amount(app):
    """Verification fails if Safepay reports a lower or different amount than appointment charges."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'state': 'TRACKER_ENDED',
            'amount': 250.0,  # Paid only Rs. 250 instead of Rs. 2,500
            'currency': 'PKR'
        }
    }

    with app.app_context(), patch('requests.get', return_value=mock_resp):
        is_valid, reason, data = verify_safepay_order('track_bad_amt', expected_charges=2500.0, expected_currency='PKR')
        assert is_valid is False
        assert 'Amount mismatch' in reason


def test_safepay_verify_rejects_mismatched_currency(app):
    """Verification fails if Safepay currency is not PKR."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'state': 'TRACKER_ENDED',
            'amount': 2500.0,
            'currency': 'USD'  # Mismatched currency
        }
    }

    with app.app_context(), patch('requests.get', return_value=mock_resp):
        is_valid, reason, data = verify_safepay_order('track_bad_cur', expected_charges=2500.0, expected_currency='PKR')
        assert is_valid is False
        assert 'Currency mismatch' in reason


def test_safepay_webhook_rejects_mismatched_amount(client, test_patient, test_doctor, db_session):
    """Safepay webhook must return HTTP 400 and NOT approve appointment if amount mismatches."""
    tracker = 'track_webhook_mismatch_test'
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date='2026-11-21',
        appointment_time='14:00:00',
        status='pending',
        payment_status='pending',
        payment_screenshot=f'safepay_pending_{tracker}',
        charges=2500.0,
        disease_category='Cardiology',
        appointment_type='online'
    )
    db_session.add(appt)
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'state': 'TRACKER_ENDED',
            'amount': 100.0,  # Underpaid
            'currency': 'PKR'
        }
    }

    with patch('requests.get', return_value=mock_resp):
        res = client.post('/safepay/webhook', json={'tracker_token': tracker, 'state': 'TRACKER_ENDED'})
        assert res.status_code == 400
        assert res.json.get('status') == 'rejected'

    db_session.refresh(appt)
    assert appt.payment_status == 'pending'

    # Cleanup
    db_session.delete(appt)
    db_session.commit()


def test_safepay_webhook_approves_matching_amount(client, test_patient, test_doctor, db_session):
    """Safepay webhook must approve appointment when amount matches charges exactly."""
    tracker = 'track_webhook_match_test'
    appt = Appointment(
        patient_id=test_patient.patient_profile.id,
        doctor_id=test_doctor.doctor_profile.id,
        appointment_date='2026-11-22',
        appointment_time='15:00:00',
        status='pending',
        payment_status='pending',
        payment_screenshot=f'safepay_pending_{tracker}',
        charges=2500.0,
        disease_category='Cardiology',
        appointment_type='online'
    )
    db_session.add(appt)
    db_session.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'data': {
            'state': 'TRACKER_ENDED',
            'amount': 2500.0,
            'currency': 'PKR'
        }
    }

    with patch('requests.get', return_value=mock_resp):
        res = client.post('/safepay/webhook', json={'tracker_token': tracker, 'state': 'TRACKER_ENDED'})
        assert res.status_code == 200
        assert res.json.get('status') == 'ok'

    db_session.refresh(appt)
    assert appt.payment_status == 'approved'
    assert appt.payment_approved_at is not None

    # Cleanup
    db_session.delete(appt)
    db_session.commit()
