import pytest
from unittest.mock import patch
from app.services.email_service import (
    send_welcome_patient_email,
    send_welcome_doctor_email,
    send_appointment_request_email,
    send_appointment_confirmation_email,
    send_appointment_rejection_email,
    send_manual_payment_admin_notification,
    send_appointment_approved_email,
)


def test_appointment_request_email_escapes_html(app):
    """Test that patient name and symptoms in appointment request email are HTML-escaped."""
    with app.app_context(), patch('app.services.email_service.send_email') as mock_send:
        send_appointment_request_email(
            doctor_email='doc@example.com',
            doctor_name='Dr. Strange',
            patient_name='Alice <script>alert(1)</script>',
            appointment_date='2026-12-01',
            appointment_time='10:00 AM',
            appointment_type='video',
            disease_category='Cardiology',
            symptoms='<b>Chest Pain</b> & dizziness'
        )

        assert mock_send.called
        call_args = mock_send.call_args[0]
        template = call_args[2]

        assert '<script>' not in template
        assert '&lt;script&gt;' in template
        assert '<b>Chest Pain</b>' not in template
        assert '&lt;b&gt;Chest Pain&lt;/b&gt;' in template


def test_appointment_rejection_email_escapes_reason(app):
    """Test that doctor rejection reason is HTML-escaped in email body."""
    with app.app_context(), patch('app.services.email_service.send_email') as mock_send:
        send_appointment_rejection_email(
            patient_email='patient@example.com',
            patient_name='Bob',
            doctor_name='Dr. House',
            reason='<img src=x onerror=alert(1)> Not available'
        )

        assert mock_send.called
        call_args = mock_send.call_args[0]
        template = call_args[2]

        assert '<img src=x onerror=alert(1)>' not in template
        assert '&lt;img src=x onerror=alert(1)&gt;' in template


def test_welcome_emails_escape_names(app):
    """Test that welcome emails escape user names containing HTML tags."""
    with app.app_context(), patch('app.services.email_service.send_email') as mock_send:
        send_welcome_patient_email('p@example.com', 'Jane <i>Doe</i>')
        template_patient = mock_send.call_args[0][2]
        assert '<i>Doe</i>' not in template_patient
        assert '&lt;i&gt;Doe&lt;/i&gt;' in template_patient

    with app.app_context(), patch('app.services.email_service.send_email') as mock_send:
        send_welcome_doctor_email('d@example.com', 'Dr. Evil <iframe>')
        template_doctor = mock_send.call_args[0][2]
        assert '<iframe>' not in template_doctor
        assert '&lt;iframe&gt;' in template_doctor


def test_manual_payment_notification_escapes_user_input(app):
    """Test that payment notification to admin escapes patient name and payment method."""
    with app.app_context(), patch('app.services.email_service.send_email') as mock_send:
        send_manual_payment_admin_notification(
            patient_name='Mallory <script>',
            doctor_name='Dr. Smith',
            appointment_date='2026-12-05',
            charges='1000',
            payment_method='<b>EasyPaisa</b>'
        )

        assert mock_send.called
        template = mock_send.call_args[0][2]
        assert '<script>' not in template
        assert '&lt;script&gt;' in template
        assert '<b>EasyPaisa</b>' not in template
        assert '&lt;b&gt;EasyPaisa&lt;/b&gt;' in template
