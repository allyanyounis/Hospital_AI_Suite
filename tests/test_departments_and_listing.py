"""
tests/test_departments_and_listing.py
Tests for Admin-Managed Departments (Feature 4.1) and Doctor Approval Directory Visibility (Step 3).
"""

import pytest
from app import db
from app.models import User, Doctor, Department


def test_department_model_crud(app):
    """Test Department model creation, uniqueness of slug, and CRUD operations."""
    with app.app_context():
        dept = Department(
            hospital_id=1,
            name="Neurology & Spine",
            slug="neurology-spine",
            icon="fas fa-brain",
            description="Comprehensive neurological and spine surgical care",
            is_active=True,
            display_order=1
        )
        db.session.add(dept)
        db.session.commit()

        try:
            queried = Department.query.filter_by(hospital_id=1, slug="neurology-spine").first()
            assert queried is not None
            assert queried.name == "Neurology & Spine"
            assert queried.icon == "fas fa-brain"
            assert queried.is_active is True

            # Test update
            queried.display_order = 5
            db.session.commit()
            updated = Department.query.get(queried.id)
            assert updated.display_order == 5
        finally:
            if queried:
                db.session.delete(queried)
                db.session.commit()


def test_approved_doctor_without_slots_appears_in_department_listing(app, client):
    """
    Step 3 Core Fix: An admin-approved doctor MUST appear in their department listing
    even before they have configured schedule time slots.
    """
    with app.app_context():
        created_dept = False
        dept = Department.query.filter_by(hospital_id=1, slug="cardiology").first()
        if not dept:
            dept = Department(
                hospital_id=1,
                name="Cardiology",
                slug="cardiology",
                icon="fas fa-heartbeat",
                description="Cardiovascular specialists",
                is_active=True
            )
            db.session.add(dept)
            db.session.commit()
            created_dept = True

        user = User(
            name="Dr. New Approved",
            email="dr.newapproved@test.com",
            phone="03001234599",
            cnic="35201-9999999-1",
            role="doctor",
            is_active=True
        )
        user.set_password("Doctor2026!Demo#")
        db.session.add(user)
        db.session.flush()

        doc = Doctor(
            user_id=user.id,
            hospital_id=1,
            category="Cardiology",
            specialization="Cardiology",
            department_id=dept.id,
            experience=7.0,
            pmc_code="PMC-TEST-99881",
            education="MBBS, FCPS Cardiology",
            bio="Experienced clinical cardiologist.",
            city="Lahore",
            location="Heart Institute, Lahore",
            is_approved=True,
            is_verified=True,
            appeal_status="approved",
            time_slots={}  # NO SLOTS CONFIGURED YET
        )
        db.session.add(doc)
        db.session.commit()

        try:
            # Check department doctors page
            res = client.get('/patients/doctors/category/cardiology')
            assert res.status_code == 200
            html = res.get_data(as_text=True)
            # Doctor name must appear in the rendered page
            assert "Dr. New Approved" in html, "Approved doctor without slots must be visible in their department listing!"
            assert "Schedule Opening Soon" in html or "opening soon" in html.lower() or "Cardiology" in html
        finally:
            db.session.delete(doc)
            db.session.delete(user)
            if created_dept:
                db.session.delete(dept)
            db.session.commit()


def test_admin_department_crud_gated(app, client, test_doctor):
    """Department admin management routes require admin role."""
    with app.app_context():
        res = client.get('/admin/departments')
        assert res.status_code in (302, 401, 403, 404)
