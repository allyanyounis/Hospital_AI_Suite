"""
tests/test_geocoding.py
Tests for Doctor clinic address geocoding on profile save (Item 6).
"""

from unittest.mock import patch
from app.models import Doctor, User


def test_doctor_profile_save_triggers_geocoding(client, test_doctor, db_session):
    """Saving doctor profile with new clinic address calls geocoder and updates coordinates."""
    doc = test_doctor.doctor_profile
    assert doc is not None

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'

    # Mock geocode_address to return coordinates for DHA Lahore
    with patch('app.utils.geocoding.geocode_address', return_value=(31.4700, 74.4100, "DHA Phase 5, Lahore, Pakistan")) as mock_geo:
        res = client.post('/doctors/profile/edit', data={
            'specialization': doc.specialization,
            'education': doc.education,
            'bio': doc.bio,
            'location': 'DHA Phase 5 Clinic, Lahore',
            'services': 'ECG, Echocardiogram'
        }, follow_redirects=True)

        assert res.status_code == 200

        # Verify doctor location and coordinates updated
        db_session.refresh(doc)
        assert doc.location == 'DHA Phase 5 Clinic, Lahore'
        assert doc.latitude == 31.4700
        assert doc.longitude == 74.4100
        assert mock_geo.called, "geocode_address must be called when doctor updates their clinic location!"


def test_doctor_profile_save_graceful_when_geocoding_fails(client, test_doctor, db_session):
    """If geocoding returns None (offline/invalid key), location is updated without crashing."""
    doc = test_doctor.doctor_profile
    initial_lat = doc.latitude

    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'

    with patch('app.utils.geocoding.geocode_address', return_value=(None, None, None)):
        res = client.post('/doctors/profile/edit', data={
            'specialization': doc.specialization,
            'education': doc.education,
            'bio': doc.bio,
            'location': 'Remote Clinic, Somewhere',
            'services': 'Consultation'
        }, follow_redirects=True)

        assert res.status_code == 200
        db_session.refresh(doc)
        assert doc.location == 'Remote Clinic, Somewhere'

