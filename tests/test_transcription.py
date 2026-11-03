"""
tests/test_transcription.py
Tests for Feature 4.5: Consultation Voice Transcription Prototype with Dual-Consent.
"""

import os
import io
import pytest
from app import db
from app.models import Appointment, Doctor, Patient, User


@pytest.fixture
def transcription_appointment(app, test_patient, test_doctor):
    """Create an approved video appointment for testing transcription."""
    with app.app_context():
        doctor = test_doctor.doctor_profile

        # Create appointment
        from datetime import date, time
        appt = Appointment(
            patient_id=test_patient.patient_profile.id,
            doctor_id=doctor.id,
            appointment_type='video',
            appointment_date=date.today(),
            appointment_time=time(14, 0),
            duration=30,
            status='approved',
            charges=2000.0,
            disease_category='Cardiology',
            symptoms='Intermittent chest palpitations after meals.',
            notes='Patient has requested consultation recording.',
            payment_status='approved',
            is_call_active=True,
            doctor_joined_video=True,
            patient_joined_video=True,
            doctor_transcript_consent=False,
            patient_transcript_consent=False
        )
        db.session.add(appt)
        db.session.commit()
        appt_id = appt.id

        yield {
            "appointment_id": appt_id,
            "patient_user_id": test_patient.id,
            "doctor_user_id": test_doctor.id
        }

        # Cleanup
        to_del = Appointment.query.get(appt_id)
        if to_del:
            db.session.delete(to_del)
            db.session.commit()


def test_dual_consent_handshake(app, client, transcription_appointment):
    """Both doctor and patient must provide explicit consent before transcription becomes active."""
    appt_id = transcription_appointment["appointment_id"]
    doc_id = transcription_appointment["doctor_user_id"]
    pat_id = transcription_appointment["patient_user_id"]

    # 1. Doctor consents
    with client.session_transaction() as sess:
        sess['user_id'] = doc_id
        sess['user_role'] = 'doctor'

    res1 = client.post(f'/video/{appt_id}/consent-transcription', json={'consent': True})
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1['success'] is True
    assert data1['consent_state']['doctor_consent'] is True
    assert data1['consent_state']['both_consented'] is False  # Patient hasn't consented yet

    # 2. Patient consents
    with client.session_transaction() as sess:
        sess['user_id'] = pat_id
        sess['user_role'] = 'patient'

    res2 = client.post(f'/video/{appt_id}/consent-transcription', json={'consent': True})
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2['success'] is True
    assert data2['consent_state']['patient_consent'] is True
    assert data2['consent_state']['both_consented'] is True  # Now both consented!

    # 3. Check status endpoint
    res_status = client.get(f'/video/{appt_id}/transcript-consent-status')
    assert res_status.status_code == 200
    status_data = res_status.get_json()
    assert status_data['both_consented'] is True


def test_upload_blocked_without_dual_consent(app, client, transcription_appointment):
    """Uploading audio when only one party consented must be rejected with 403."""
    appt_id = transcription_appointment["appointment_id"]
    pat_id = transcription_appointment["patient_user_id"]

    with app.app_context():
        appt = Appointment.query.get(appt_id)
        appt.doctor_transcript_consent = True
        appt.patient_transcript_consent = False  # Patient has not consented!
        db.session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = pat_id
        sess['user_role'] = 'patient'

    fake_audio = io.BytesIO(b"MOCK_AUDIO_PAYLOAD_BYTES")
    res = client.post(
        f'/video/{appt_id}/upload-transcript-audio',
        data={'audio': (fake_audio, 'consultation.webm', 'audio/webm')},
        content_type='multipart/form-data'
    )
    assert res.status_code == 403
    assert "Dual consent required" in res.get_json().get('error', '')


def test_upload_success_and_immediate_audio_deletion(app, client, transcription_appointment):
    """
    When dual consent is granted:
    1. Audio is transcribed and attached to appointment record.
    2. Raw audio is immediately deleted from disk (zero-audio retention policy).
    """
    appt_id = transcription_appointment["appointment_id"]
    doc_id = transcription_appointment["doctor_user_id"]
    pat_id = transcription_appointment["patient_user_id"]

    # Doctor consents via endpoint
    with client.session_transaction() as sess:
        sess['user_id'] = doc_id
        sess['user_role'] = 'doctor'
    client.post(f'/video/{appt_id}/consent-transcription', json={'consent': True})

    # Patient consents via endpoint
    with client.session_transaction() as sess:
        sess['user_id'] = pat_id
        sess['user_role'] = 'patient'
    client.post(f'/video/{appt_id}/consent-transcription', json={'consent': True})

    # Doctor uploads audio
    with client.session_transaction() as sess:
        sess['user_id'] = doc_id
        sess['user_role'] = 'doctor'

    fake_audio = io.BytesIO(b"RIFF....WAVEfmt....dataMockConsultationAudioContent")
    res = client.post(
        f'/video/{appt_id}/upload-transcript-audio',
        data={'audio': (fake_audio, 'recording.webm', 'audio/webm')},
        content_type='multipart/form-data'
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert "CONSULTATION VOICE TRANSCRIPT" in data['transcript']

    # Verify database persistence
    with app.app_context():
        saved = Appointment.query.get(appt_id)
        assert saved.consultation_transcript is not None
        assert "Doctor:" in saved.consultation_transcript
        assert "Patient:" in saved.consultation_transcript
        assert saved.transcript_created_at is not None

        # Verify no audio files remain in temp folder
        temp_dir = os.path.join(app.instance_path, 'temp_transcripts')
        if os.path.exists(temp_dir):
            remaining = [f for f in os.listdir(temp_dir) if f.startswith(f"audio_{appt_id}")]
            assert len(remaining) == 0, f"Expected 0 remaining audio files, found {remaining}"
