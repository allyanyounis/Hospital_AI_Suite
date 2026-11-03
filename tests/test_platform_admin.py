"""
tests/test_platform_admin.py
Integration tests for Aramis Health Platform Super Admin Console.
"""

import pytest
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Hospital, HospitalMembership, AdminAuditLog

@pytest.fixture
def platform_super_admin(app, db_session):
    u = User.query.filter_by(role='platform_super_admin').first()
    if not u:
        u = User.query.filter_by(email='superadmin@example.com').first()
        if u:
            u.role = 'platform_super_admin'
            db_session.commit()
        else:
            u = User(
                name='Platform Super Admin',
                email='superadmin@example.com',
                phone='+923000000001',
                cnic='35201-1000001-1',
                role='platform_super_admin',
                is_active=True,
                password_hash=generate_password_hash('Admin123!')
            )
            db_session.add(u)
            db_session.commit()
    return u

def test_platform_admin_access_unauthorized(client):
    """Anonymous visitors are redirected to login."""
    res = client.get('/admin/platform/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/auth/login' in res.headers['Location']

def test_platform_admin_access_forbidden_for_patient(client, test_patient):
    """Regular patients are blocked with 403 Forbidden."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_patient.id
        sess['user_role'] = 'patient'
        sess['user_name'] = test_patient.name

    res = client.get('/admin/platform/dashboard')
    assert res.status_code == 403

def test_platform_admin_dashboard_metrics(client, platform_super_admin):
    """Platform super admin can view cross-tenant metrics and all hospital tenants."""
    with client.session_transaction() as sess:
        sess['user_id'] = platform_super_admin.id
        sess['user_role'] = 'platform_super_admin'
        sess['user_name'] = platform_super_admin.name

    res = client.get('/admin/platform/dashboard', follow_redirects=True)
    assert res.status_code == 200
    assert b"Platform Super Admin Console" in res.data
    assert b"Aramis Demo Hospital" in res.data
    assert b"Aramis City Clinic" in res.data
    assert b"BYPASSRLS Live" in res.data

def test_platform_admin_create_hospital(client, app, platform_super_admin):
    """Platform super admin can provision a new hospital tenant."""
    with client.session_transaction() as sess:
        sess['user_id'] = platform_super_admin.id
        sess['user_role'] = 'platform_super_admin'
        sess['user_name'] = platform_super_admin.name

    payload = {
        'name': 'Aramis Valley Hospital',
        'city': 'Rawalpindi',
        'address': 'Plot 10, Medical Boulevard, Rawalpindi',
        'commission_percent': '18.5'
    }

    res = client.post('/admin/platform/hospitals/new', data=payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"successfully provisioned" in res.data or b"Aramis Valley Hospital" in res.data

    with app.app_context():
        h = Hospital.query.filter_by(slug='aramis-valley-hospital').first()
        assert h is not None
        assert h.city == 'Rawalpindi'
        assert h.status == 'active'

def test_platform_admin_toggle_hospital_status(client, app, platform_super_admin):
    """Platform super admin can suspend and reactivate a hospital tenant."""
    from app.services.tenant_context import get_platform_session
    plat_sess = get_platform_session()
    try:
        h = plat_sess.query(Hospital).filter_by(slug='aramis-city-clinic').first()
        assert h is not None
        h_id = h.id
    finally:
        plat_sess.close()

    with client.session_transaction() as sess:
        sess['user_id'] = platform_super_admin.id
        sess['user_role'] = 'platform_super_admin'
        sess['user_name'] = platform_super_admin.name

    try:
        # Suspend
        res = client.post(f'/admin/platform/hospitals/{h_id}/toggle-status', follow_redirects=True)
        assert res.status_code == 200
        assert b"status updated" in res.data

        plat_sess = get_platform_session()
        try:
            h_updated = plat_sess.get(Hospital, h_id)
            assert h_updated.status == 'suspended'
        finally:
            plat_sess.close()

        # Reactivate
        res = client.post(f'/admin/platform/hospitals/{h_id}/toggle-status', follow_redirects=True)
        assert res.status_code == 200

        plat_sess = get_platform_session()
        try:
            h_reactivated = plat_sess.get(Hospital, h_id)
            assert h_reactivated.status == 'active'
        finally:
            plat_sess.close()
    finally:
        plat_sess = get_platform_session()
        try:
            h_clean = plat_sess.get(Hospital, h_id)
            if h_clean and h_clean.status != 'active':
                h_clean.status = 'active'
                plat_sess.commit()
        finally:
            plat_sess.close()

def test_platform_admin_onboard_hospital_admin(client, app, platform_super_admin):
    """Platform super admin can onboard an executive Hospital Admin."""
    from app.services.tenant_context import get_platform_session
    plat_sess = get_platform_session()
    try:
        h = plat_sess.query(Hospital).filter_by(slug='aramis-city-clinic').first()
        assert h is not None
        h_id = h.id
    finally:
        plat_sess.close()

    with client.session_transaction() as sess:
        sess['user_id'] = platform_super_admin.id
        sess['user_role'] = 'platform_super_admin'
        sess['user_name'] = platform_super_admin.name

    payload = {
        'name': 'Dr. Kamran Malik',
        'email': 'admin.test.city@aramis.health',
        'phone': '+923009998877',
        'cnic': '35202-9998877-1',
        'password': 'Password123!'
    }

    try:
        res = client.post(f'/admin/platform/hospitals/{h_id}/onboard-admin', data=payload, follow_redirects=True)
        assert res.status_code == 200
        assert b"successfully assigned as Hospital Admin" in res.data

        with app.app_context():
            u = User.query.filter_by(email='admin.test.city@aramis.health').first()
            assert u is not None
            assert u.role == 'admin'

            plat_sess = get_platform_session()
            try:
                mem = plat_sess.query(HospitalMembership).filter_by(user_id=u.id, hospital_id=h_id, role='hospital_admin').first()
                assert mem is not None
                assert mem.status == 'active'
            finally:
                plat_sess.close()
    finally:
        with app.app_context():
            u = User.query.filter_by(email='admin.test.city@aramis.health').first()
            if u:
                db.session.delete(u)
                db.session.commit()

