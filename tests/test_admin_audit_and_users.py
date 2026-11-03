"""
tests/test_admin_audit_and_users.py
Tests for Admin User Management Directory, Role/Status Filtering, and Admin Audit Logging.
"""

import pytest
from app.models import AdminAuditLog, Doctor, User

def test_admin_users_view_and_filters(client, test_admin, app, test_doctor, test_patient):
    """Verify GET /admin/users lists users and applies role/status/search filters."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'

    # 1. Base view
    res = client.get('/admin/users')
    assert res.status_code == 200
    assert b'User Management Directory' in res.data

    # 2. Filter by role=doctor + search
    res_doc = client.get(f'/admin/users?role=doctor&q={test_doctor.name}')
    assert res_doc.status_code == 200
    assert test_doctor.name.encode() in res_doc.data

    # 3. Filter by role=patient + search
    res_pat = client.get(f'/admin/users?role=patient&q={test_patient.name}')
    assert res_pat.status_code == 200
    assert test_patient.name.encode() in res_pat.data

    # 4. Search query
    res_search = client.get(f'/admin/users?q={test_doctor.name}')
    assert res_search.status_code == 200
    assert test_doctor.name.encode() in res_search.data


def test_toggle_doctor_status_records_audit(client, test_admin, test_doctor, app, db_session):
    """Verify toggling doctor status records an admin audit log entry."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'

    doctor_profile = test_doctor.doctor_profile
    res = client.post(f'/admin/doctors/{doctor_profile.id}/toggle-status', follow_redirects=True)
    assert res.status_code == 200

    # Verify audit log was written
    log = AdminAuditLog.query.filter_by(
        admin_id=test_admin.id,
        action='toggle_doctor_status'
    ).first()

    assert log is not None
    assert log.ip_address is not None
    assert log.target_id == doctor_profile.id


def test_admin_audit_logs_view_and_filter(client, test_admin, app, db_session):
    """Verify admin audit log viewer renders and supports filtering."""
    # Write a test log
    test_log = AdminAuditLog(
        hospital_id=1,
        admin_id=test_admin.id,
        action='test_action',
        target_type='system',
        target_id=1,
        details='test suite verification',
        ip_address='127.0.0.1'
    )
    db_session.add(test_log)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['user_role'] = 'admin'

    # View list
    res = client.get('/admin/audit-logs')
    assert res.status_code == 200
    assert b'Administrative Audit Logs' in res.data
    assert b'test_action' in res.data

    # Filter by action
    res_action = client.get('/admin/audit-logs?action=test_action')
    assert res_action.status_code == 200
    assert b'test_action' in res_action.data

    # Clean up
    db_session.delete(test_log)
    db_session.commit()


def test_unauthorized_user_cannot_view_admin_users(client, test_patient):
    """Verify non-admin cannot view /admin/users."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'

    res = client.get('/admin/users', follow_redirects=False)
    assert res.status_code in (302, 403)


def test_unauthorized_user_cannot_view_audit_logs(client, test_doctor):
    """Verify doctor cannot view /admin/audit-logs."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_doctor.id
        sess['user_role'] = 'doctor'

    res = client.get('/admin/audit-logs', follow_redirects=False)
    assert res.status_code in (302, 403)
