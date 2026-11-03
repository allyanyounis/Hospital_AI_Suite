"""
tests/test_tenant_permissions.py
Unit tests verifying Aramis Health hospital role hierarchy, anti-escalation rules,
finance-clinical segregation, and audit logging.
"""

import pytest
from werkzeug.exceptions import NotFound
from app import db
from app.models import User, Hospital, HospitalMembership, Department, AdminAuditLog
from app.utils.tenant_permissions import (
    can_manage_membership,
    is_finance_role,
    assert_clinical_access_allowed,
    sanitize_clinical_payload_for_finance,
    audit_membership_change,
    get_role_level
)

class MockAppointment:
    def __init__(self):
        self.id = 99
        self.hospital_id = 1
        self.patient_id = 1
        self.doctor_id = 2
        self.appointment_type = 'video'
        self.appointment_date = None
        self.appointment_time = None
        self.status = 'completed'
        self.charges = 2500.0
        self.payment_status = 'approved'
        self.platform_commission_amount = 500.0
        self.payment_approved_at = None
        self.disease_category = 'Cardiology'
        self.symptoms = 'Chest tightness and shortness of breath.'
        self.notes = 'Clinical consultation notes.'
        self.consultation_transcript = 'Patient: I felt dizzy. Doctor: Let us review your ECG.'

def test_role_hierarchy_numeric_ranks():
    """Verify numeric levels match the 4-level reporting hierarchy."""
    assert get_role_level('platform_super_admin') == 0
    assert get_role_level('hospital_admin') == 1
    assert get_role_level('medical_director') == 2
    assert get_role_level('operations_manager') == 2
    assert get_role_level('finance_manager') == 2
    assert get_role_level('hr_it_manager') == 2
    assert get_role_level('hod') == 3
    assert get_role_level('doctor') == 4
    assert get_role_level('nurse') == 4
    assert get_role_level('accountant') == 4
    assert get_role_level('patient') == 99

def test_anti_privilege_escalation_rules(app):
    """Verify strict anti-escalation enforcement."""
    with app.app_context():
        # Setup actors
        u_ha = User.query.filter_by(email='admin.demo@aramis.health').first()
        u_md = User.query.filter_by(email='director.demo@aramis.health').first()
        u_hod = User.query.filter_by(email='dr.tariq@example.com').first()
        u_nurse = User.query.filter_by(email='nurse.demo@aramis.health').first()

        dept_cardio = Department.query.filter_by(hospital_id=1, slug='cardiology').first()
        dept_neuro = Department.query.filter_by(hospital_id=1, slug='neurology').first()

        # 1. Hospital Admin can manage Medical Director (level 2) and HOD (level 3)
        ok, msg = can_manage_membership(u_ha, 1, 'medical_director', target_user_id=999)
        assert ok is True
        ok, msg = can_manage_membership(u_ha, 1, 'hod', target_department_id=dept_cardio.id if dept_cardio else None, target_user_id=999)
        assert ok is True

        # 2. Hospital Admin CANNOT assign Hospital Admin (equal level) or Super Admin (higher)
        ok, msg = can_manage_membership(u_ha, 1, 'hospital_admin', target_user_id=999)
        assert ok is False
        assert "Privilege escalation denied" in msg

        ok, msg = can_manage_membership(u_ha, 1, 'platform_super_admin', target_user_id=999)
        assert ok is False

        # 3. Medical Director (level 2 clinical) can manage HOD (level 3) and Doctor (level 4)
        ok, msg = can_manage_membership(u_md, 1, 'hod', target_department_id=dept_cardio.id if dept_cardio else None, target_user_id=999)
        assert ok is True

        # Medical Director CANNOT assign Accountant (finance domain)
        ok, msg = can_manage_membership(u_md, 1, 'accountant', target_user_id=999)
        assert ok is False
        assert "Cross-domain assignment denied" in msg

        # 4. HOD (level 3, cardio) can manage Doctor (level 4) in own cardio department
        if dept_cardio:
            ok, msg = can_manage_membership(u_hod, 1, 'doctor', target_department_id=dept_cardio.id, target_user_id=999)
            assert ok is True

            # HOD CANNOT manage Doctor in other department (e.g. neurology)
            if dept_neuro:
                ok, msg = can_manage_membership(u_hod, 1, 'doctor', target_department_id=dept_neuro.id, target_user_id=999)
                assert ok is False
                assert "own department" in msg

            # HOD CANNOT manage another HOD or Manager
            ok, msg = can_manage_membership(u_hod, 1, 'hod', target_department_id=dept_cardio.id, target_user_id=999)
            assert ok is False

        # 5. Staff (level 4) CANNOT manage any membership
        ok, msg = can_manage_membership(u_nurse, 1, 'nurse', target_user_id=999)
        assert ok is False

        # 6. No self-promotion
        ok, msg = can_manage_membership(u_ha, 1, 'hospital_admin', target_user_id=u_ha.id)
        assert ok is False
        assert "own membership" in msg

def test_finance_clinical_segregation():
    """Verify finance roles are blocked from clinical payloads."""
    assert is_finance_role('accountant') is True
    assert is_finance_role('finance_manager') is True
    assert is_finance_role('doctor') is False
    assert is_finance_role('hospital_admin') is False

    # Blocked check
    with pytest.raises(NotFound):
        assert_clinical_access_allowed('accountant', 'Prescription #12')

    with pytest.raises(NotFound):
        assert_clinical_access_allowed('finance_manager', 'Medical Document #5')

    # Allowed for clinical roles
    assert_clinical_access_allowed('doctor', 'Prescription #12')
    assert_clinical_access_allowed('nurse', 'Prescription #12')

    # Payload redaction
    mock_appt = MockAppointment()
    sanitized_finance = sanitize_clinical_payload_for_finance(mock_appt, 'accountant')
    assert sanitized_finance['charges'] == 2500.0
    assert sanitized_finance['payment_status'] == 'approved'
    assert sanitized_finance['disease_category'] == '[RESTRICTED_FINANCE_VIEW]'
    assert sanitized_finance['symptoms'] == '[RESTRICTED_FINANCE_VIEW]'
    assert sanitized_finance['consultation_transcript'] is None

    sanitized_doctor = sanitize_clinical_payload_for_finance(mock_appt, 'doctor')
    assert sanitized_doctor['symptoms'] == 'Chest tightness and shortness of breath.'
    assert sanitized_doctor['consultation_transcript'] is not None

def test_tenant_membership_audit_log(app):
    """Verify membership changes are logged to AdminAuditLog."""
    with app.app_context():
        u_ha = User.query.filter_by(email='admin.demo@aramis.health').first()
        assert u_ha is not None

        log_entry = audit_membership_change(
            actor_id=u_ha.id,
            hospital_id=1,
            action='assign_role',
            target_user_id=999,
            target_role='nurse',
            details='Assigned to Cardiology ward night shift'
        )

        assert log_entry.id is not None
        assert log_entry.hospital_id == 1
        assert log_entry.admin_id == u_ha.id
        assert log_entry.action == 'assign_role'
        assert log_entry.target_id == 999
        assert 'Cardiology' in log_entry.details

