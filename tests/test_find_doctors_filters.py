"""
tests/test_find_doctors_filters.py
Tests for Feature 4.3 (Find Doctors Filters, Geolocation Distance, and Sorting) and Feature 4.2.
"""

import pytest
from app import db
from app.models import User, Doctor, Department


@pytest.fixture
def filter_test_doctors(app):
    """Seed test doctors with varied fees, ratings, experience, and coordinates."""
    with app.app_context():
        dept = Department.query.filter_by(hospital_id=1, slug="cardiology").first()
        if not dept:
            dept = Department(hospital_id=1, name="Cardiology", slug="cardiology", icon="fas fa-heartbeat", is_active=True)
            db.session.add(dept)
            db.session.commit()

        # Clean prior test artifacts if any
        existing_u1 = User.query.filter_by(email="doc.alpha@filter.test").first()
        if existing_u1:
            Doctor.query.filter_by(user_id=existing_u1.id).delete()
            db.session.delete(existing_u1)
            db.session.commit()

        existing_u2 = User.query.filter_by(email="doc.beta@filter.test").first()
        if existing_u2:
            Doctor.query.filter_by(user_id=existing_u2.id).delete()
            db.session.delete(existing_u2)
            db.session.commit()

        # Doctor 1: Lahore (low fee, 15 yrs exp)
        u1 = User(name="Dr. Filter Alpha", email="doc.alpha@filter.test", phone="03001111111", cnic="35201-1111111-1", role="doctor", gender="male", is_active=True)
        u1.set_password("Doctor2026!Demo#")
        db.session.add(u1)
        db.session.flush()

        d1 = Doctor(
            user_id=u1.id,
            hospital_id=1,
            category="Cardiology", specialization="Cardiology", department_id=dept.id,
            experience=15.0, pmc_code="PMC-F1", education="MBBS, FCPS", bio="Alpha bio",
            city="Lahore", location="Doctors Hospital, Lahore", latitude=31.5204, longitude=74.3587,
            is_approved=True, is_verified=True, appeal_status="approved",
            time_slots={
                'monday': {'hospital': 'Doctors Hospital', 'start_time': '09:00', 'end_time': '17:00', 'duration': 30, 'physical_price': 1500, 'video_price': 1000}
            }
        )
        db.session.add(d1)

        # Doctor 2: Karachi (high fee, female, 5 yrs exp)
        u2 = User(name="Dr. Filter Beta", email="doc.beta@filter.test", phone="03002222222", cnic="35201-2222222-1", role="doctor", gender="female", is_active=True)
        u2.set_password("Doctor2026!Demo#")
        db.session.add(u2)
        db.session.flush()

        d2 = Doctor(
            user_id=u2.id,
            hospital_id=1,
            category="Cardiology", specialization="Cardiology", department_id=dept.id,
            experience=5.0, pmc_code="PMC-F2", education="MBBS, MD", bio="Beta bio",
            city="Karachi", location="Aga Khan Hospital, Karachi", latitude=24.8607, longitude=67.0011,
            is_approved=True, is_verified=True, appeal_status="approved",
            time_slots={
                'monday': {'hospital': 'Aga Khan Hospital', 'start_time': '10:00', 'end_time': '14:00', 'duration': 30, 'physical_price': 4000, 'video_price': 3500}
            }
        )
        db.session.add(d2)
        db.session.commit()

        try:
            yield {
                "d1_id": d1.id,
                "d2_id": d2.id,
                "dept_id": dept.id
            }
        finally:
            try:
                db.session.delete(d1)
                db.session.delete(u1)
                db.session.delete(d2)
                db.session.delete(u2)
                db.session.commit()
            except Exception:
                db.session.rollback()


def test_gender_and_city_filtering(client, filter_test_doctors):
    """Test filtering by gender and city."""
    # Filter by male in Lahore
    res = client.get('/patients/doctors/category/cardiology?gender=male&city=Lahore')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Dr. Filter Alpha" in html
    assert "Dr. Filter Beta" not in html

    # Filter by female in Karachi
    res2 = client.get('/patients/doctors/category/cardiology?gender=female&city=Karachi')
    assert res2.status_code == 200
    html2 = res2.get_data(as_text=True)
    assert "Dr. Filter Beta" in html2
    assert "Dr. Filter Alpha" not in html2


def test_fee_range_filtering(client, filter_test_doctors):
    """Test filtering by fee brackets."""
    # Below 2000 bracket: Dr. Alpha has video 1000, physical 1500
    res = client.get('/patients/doctors/category/cardiology?fee_range=1000_2000')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Dr. Filter Alpha" in html
    assert "Dr. Filter Beta" not in html

    # 3000 to 5000 bracket: Dr. Beta has 3500/4000
    res2 = client.get('/patients/doctors/category/cardiology?fee_range=3000_5000')
    assert res2.status_code == 200
    html2 = res2.get_data(as_text=True)
    assert "Dr. Filter Beta" in html2
    assert "Dr. Filter Alpha" not in html2


def test_geolocation_near_me_sorting(client, filter_test_doctors):
    """Test Haversine distance sorting when user coordinates are supplied."""
    # User is in Lahore (near Dr. Alpha)
    res = client.get('/patients/doctors/category/cardiology?sort=nearest&lat=31.52&lng=74.35')
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    pos_alpha = html.find("Dr. Filter Alpha")
    pos_beta = html.find("Dr. Filter Beta")
    assert pos_alpha != -1 and pos_beta != -1
    assert pos_alpha < pos_beta, "Dr. Alpha (Lahore) must appear before Dr. Beta (Karachi) when sorting nearest to Lahore!"
    assert "km away" in html
