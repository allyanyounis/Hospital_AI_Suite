"""
tests/test_hospital_org_chart.py
Integration tests for Aramis Health Hospital Org Chart and Scoped Department Staff.
"""

import pytest
from app import db
from app.models import User, Hospital, HospitalMembership, Department

@pytest.fixture
def hospital_admin_user(app):
    return User.query.filter_by(email='admin.demo@aramis.health').first()

@pytest.fixture
def hod_user(app):
    return User.query.filter_by(email='dr.tariq@example.com').first()

def test_org_chart_renders_for_hospital_admin(client, hospital_admin_user):
    """Hospital admin can view the visual org chart for their hospital."""
    with client.session_transaction() as sess:
        sess['user_id'] = hospital_admin_user.id
        sess['user_role'] = 'admin'
        sess['user_name'] = hospital_admin_user.name
        sess['current_hospital_id'] = 1

    res = client.get('/admin/org-chart', follow_redirects=True)
    assert res.status_code == 200
    assert b"Organizational Hierarchy" in res.data
    assert b"Staff Reporting Tree" in res.data
    assert b"Dr. Naveed Akhtar" in res.data or b"Medical Director" in res.data
    assert b"Dr. Tariq Mahmood" in res.data

def test_assign_staff_role_anti_escalation_enforcement(client, app, hospital_admin_user):
    """Anti-privilege escalation blocks assigning roles equal to or above actor level."""
    with app.app_context():
        u_target = User.query.filter_by(email='patient.fixture@example.com').first()
        if not u_target:
            u_target = User.query.first()
        target_id = u_target.id

    with client.session_transaction() as sess:
        sess['user_id'] = hospital_admin_user.id
        sess['user_role'] = 'admin'
        sess['user_name'] = hospital_admin_user.name
        sess['current_hospital_id'] = 1

    # Attempt escalation: Hospital admin tries to assign Hospital Admin (equal rank)
    payload_invalid = {
        'user_id': target_id,
        'role': 'hospital_admin',
        'department_id': ''
    }
    res = client.post('/admin/staff/assign-role', data=payload_invalid, follow_redirects=True)
    assert res.status_code == 200
    assert b"Permission Denied" in res.data or b"escalation" in res.data

    # Valid assignment: Hospital admin assigns Nurse (Level 4)
    payload_valid = {
        'user_id': target_id,
        'role': 'nurse',
        'department_id': '1'
    }
    res_valid = client.post('/admin/staff/assign-role', data=payload_valid, follow_redirects=True)
    assert res_valid.status_code == 200
    assert b"Successfully assigned role" in res_valid.data

    with app.app_context():
        mem = HospitalMembership.query.filter_by(user_id=target_id, hospital_id=1, role='nurse').first()
        assert mem is not None
        assert mem.status == 'active'

def test_toggle_staff_membership_status(client, app, hospital_admin_user):
    """Hospital admin can suspend and reactivate a staff membership."""
    with app.app_context():
        mem = HospitalMembership.query.filter_by(hospital_id=1, role='nurse').first()
        assert mem is not None
        mem_id = mem.id

    with client.session_transaction() as sess:
        sess['user_id'] = hospital_admin_user.id
        sess['user_role'] = 'admin'
        sess['user_name'] = hospital_admin_user.name
        sess['current_hospital_id'] = 1

    # Ensure starts active
    with app.app_context():
        mem = db.session.get(HospitalMembership, mem_id)
        mem.status = 'active'
        db.session.commit()

    res = client.post(f'/admin/staff/membership/{mem_id}/toggle-status', follow_redirects=True)
    assert res.status_code == 200
    assert b"status updated to suspended" in res.data or b"status updated" in res.data

    with app.app_context():
        mem_updated = db.session.get(HospitalMembership, mem_id)
        assert mem_updated.status == 'suspended'

def test_department_staff_console_scoped_for_hod(client, hod_user):
    """HOD viewing department staff console is locked to their own department."""
    with client.session_transaction() as sess:
        sess['user_id'] = hod_user.id
        sess['user_role'] = 'doctor'
        sess['user_name'] = hod_user.name
        sess['current_hospital_id'] = 1

    res = client.get('/admin/department-staff', follow_redirects=True)
    assert res.status_code == 200
    assert b"Department Staff Console" in res.data or b"Cardiology" in res.data
    assert b"HOD Department Locked" in res.data
