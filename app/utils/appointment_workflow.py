"""Appointment booking workflow helpers (payment before doctor approval)."""

from datetime import datetime, timedelta

from app.services.email_service import send_appointment_request_email
from app.utils.timezone import get_pakistan_now, PAKISTAN_TZ


def set_booking_payment_deadline(appointment):
    """Set payment deadline when a patient first books an appointment."""
    current_time = get_pakistan_now()
    appointment_datetime = PAKISTAN_TZ.localize(
        datetime.combine(appointment.appointment_date, appointment.appointment_time)
    )
    standard_deadline = current_time + timedelta(minutes=30)
    appointment.payment_deadline = min(standard_deadline, appointment_datetime)


def appointment_awaiting_payment(appointment):
    """Patient must pay before the doctor sees the request."""
    return (
        appointment.status == 'pending'
        and appointment.payment_status in ('pending', 'rejected')
    )


def doctor_can_review_appointment(appointment):
    """Doctor may approve/reject after admin confirms payment."""
    return (
        appointment.status == 'pending'
        and appointment.payment_status == 'approved'
    )


def appointment_awaiting_doctor(appointment):
    """Admin-approved payment; doctor can approve or reject."""
    return doctor_can_review_appointment(appointment)


def notify_doctor_after_payment(appointment):
    """Email doctor once patient payment is confirmed."""
    if not appointment_awaiting_doctor(appointment):
        return

    try:
        doctor_user = appointment.doctor.user
        patient_user = appointment.patient.user
        send_appointment_request_email(
            doctor_email=doctor_user.email,
            doctor_name=doctor_user.name,
            patient_name=patient_user.name,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            appointment_type=appointment.appointment_type,
            disease_category=appointment.disease_category or 'Not specified',
            symptoms=appointment.symptoms or 'Not specified',
        )
    except Exception as e:
        print(f'Error sending appointment request email to doctor: {e}')


def on_payment_marked_approved(appointment):
    """Call after admin approves payment (before db commit)."""
    notify_doctor_after_payment(appointment)


def can_issue_prescription(appointment) -> tuple[bool, str]:
    """
    Validate whether a prescription can be issued for an appointment.
    Rules:
    - Payment must be approved.
    - Appointment must be active (status == 'approved').
    - For video appointments only: prescription_unlocked must be True (3-minute mutual video consultation).
      Physical (in-clinic) appointments bypass the video unlock requirement.
    """
    if appointment.payment_status != 'approved':
        return False, 'Cannot issue prescription: Payment has not been approved.'

    if appointment.status != 'approved':
        return False, 'Only approved appointments can be completed.'

    if appointment.appointment_type == 'video' and not getattr(appointment, 'prescription_unlocked', False):
        return False, (
            'You must complete a video consultation with the patient first: both join the call, '
            'stay connected for at least 3 minutes, then the prescription section unlocks automatically.'
        )

    return True, ''
