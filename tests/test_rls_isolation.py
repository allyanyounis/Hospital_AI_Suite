import os
import pytest
import psycopg
from urllib.parse import urlparse

def get_connection_info(role='aramis_app'):
    test_db_url = os.environ.get('APP_TEST_DATABASE_URL') or os.environ.get('TEST_DATABASE_URL') or 'postgresql://127.0.0.1:5432/quickcare_test'
    if test_db_url.startswith('postgresql+psycopg://'):
        test_db_url = test_db_url.replace('postgresql+psycopg://', 'postgresql://', 1)
    
    parsed = urlparse(test_db_url)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 5432
    dbname = parsed.path.lstrip('/') or 'quickcare_test'
    
    if role == 'aramis_platform':
        password = os.environ.get('ARAMIS_PLATFORM_PASSWORD', 'AramisPlatform2026!Sec#')
        user = 'aramis_platform'
    else:
        password = os.environ.get('ARAMIS_APP_PASSWORD', 'AramisApp2026!Sec#')
        user = 'aramis_app'
        
    return {
        'host': host,
        'port': port,
        'dbname': dbname,
        'user': user,
        'password': password
    }

@pytest.fixture
def app_conn():
    """Provides a raw psycopg connection as non-superuser aramis_app."""
    info = get_connection_info('aramis_app')
    conn = psycopg.connect(**info, autocommit=False)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()

@pytest.fixture
def platform_conn():
    """Provides a raw psycopg connection as aramis_platform (BYPASSRLS)."""
    info = get_connection_info('aramis_platform')
    conn = psycopg.connect(**info, autocommit=False)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()

def test_rls_fail_closed_when_tenant_unset(app_conn):
    """
    When app.current_hospital_id is unset or empty, RLS must fail closed:
    tenant tables return 0 rows for non-superuser aramis_app.
    """
    with app_conn.cursor() as cur:
        # Check current user is aramis_app
        cur.execute("SELECT current_user;")
        user = cur.fetchone()[0]
        assert user == 'aramis_app', f"Expected connection as aramis_app, got {user}"

        # 1. Unset GUC -> queries on tenant tables return 0 rows
        cur.execute("SELECT count(*) FROM departments;")
        count_dept = cur.fetchone()[0]
        assert count_dept == 0, f"Expected 0 departments when tenant unset, got {count_dept}"

        cur.execute("SELECT count(*) FROM appointments;")
        count_appt = cur.fetchone()[0]
        assert count_appt == 0, f"Expected 0 appointments when tenant unset, got {count_appt}"

        cur.execute("SELECT count(*) FROM doctors;")
        count_doc = cur.fetchone()[0]
        assert count_doc == 0, f"Expected 0 doctors when tenant unset, got {count_doc}"

        # 2. Explicitly setting empty string -> still returns 0 rows
        cur.execute("SET LOCAL app.current_hospital_id = '';")
        cur.execute("SELECT count(*) FROM departments;")
        count_dept_empty = cur.fetchone()[0]
        assert count_dept_empty == 0, f"Expected 0 departments when hospital_id is empty string, got {count_dept_empty}"

def test_rls_hospital_1_isolation(app_conn):
    """
    When app.current_hospital_id = '1':
    - SELECT / UPDATE / DELETE on Hospital 1 records succeeds
    - Attempted SELECT / UPDATE / DELETE on Hospital 2 records affects 0 rows
    """
    with app_conn.cursor() as cur:
        cur.execute("SET LOCAL app.current_hospital_id = '1';")
        
        # 1. SELECT returns only Hospital 1 departments
        cur.execute("SELECT id, hospital_id FROM departments;")
        h1_depts = cur.fetchall()
        assert len(h1_depts) > 0, "Hospital 1 should have departments seeded"
        assert all(row[1] == 1 for row in h1_depts), "All returned departments must belong to hospital 1"

        # 2. Attempted SELECT specifically querying for hospital_id = 2 returns 0 rows
        cur.execute("SELECT count(*) FROM departments WHERE hospital_id = 2;")
        h2_visible_count = cur.fetchone()[0]
        assert h2_visible_count == 0, f"Hospital 2 records must not be visible under hospital 1 context (got {h2_visible_count})"

        # 3. Attempted UPDATE on Hospital 2 departments affects 0 rows
        cur.execute("UPDATE departments SET description = 'Tampered' WHERE hospital_id = 2;")
        assert cur.rowcount == 0, f"Cross-tenant UPDATE must affect 0 rows, affected: {cur.rowcount}"

        # 4. Attempted DELETE on Hospital 2 departments affects 0 rows
        cur.execute("DELETE FROM departments WHERE hospital_id = 2;")
        assert cur.rowcount == 0, f"Cross-tenant DELETE must affect 0 rows, affected: {cur.rowcount}"

        # 5. Legitimate UPDATE on Hospital 1 department succeeds
        target_id = h1_depts[0][0]
        cur.execute("UPDATE departments SET description = 'Updated in H1' WHERE id = %s;", (target_id,))
        assert cur.rowcount == 1, "Legitimate tenant UPDATE on own hospital record must succeed"

def test_rls_hospital_2_isolation(app_conn):
    """
    Symmetrically, when app.current_hospital_id = '2':
    - SELECT / UPDATE / DELETE on Hospital 2 records succeeds
    - Attempted SELECT / UPDATE / DELETE on Hospital 1 records affects 0 rows
    """
    with app_conn.cursor() as cur:
        cur.execute("SET LOCAL app.current_hospital_id = '2';")

        # 1. SELECT returns only Hospital 2 departments
        cur.execute("SELECT id, hospital_id FROM departments;")
        h2_depts = cur.fetchall()
        assert len(h2_depts) > 0, "Hospital 2 should have departments seeded"
        assert all(row[1] == 2 for row in h2_depts), "All returned departments must belong to hospital 2"

        # 2. Attempted SELECT for hospital_id = 1 returns 0 rows
        cur.execute("SELECT count(*) FROM departments WHERE hospital_id = 1;")
        h1_visible_count = cur.fetchone()[0]
        assert h1_visible_count == 0, f"Hospital 1 records must not be visible under hospital 2 context (got {h1_visible_count})"

        # 3. Attempted UPDATE on Hospital 1 departments affects 0 rows
        cur.execute("UPDATE departments SET description = 'Tampered' WHERE hospital_id = 1;")
        assert cur.rowcount == 0, f"Cross-tenant UPDATE must affect 0 rows, affected: {cur.rowcount}"

        # 4. Attempted DELETE on Hospital 1 departments affects 0 rows
        cur.execute("DELETE FROM departments WHERE hospital_id = 1;")
        assert cur.rowcount == 0, f"Cross-tenant DELETE must affect 0 rows, affected: {cur.rowcount}"

        # 5. Legitimate UPDATE on Hospital 2 department succeeds
        target_id = h2_depts[0][0]
        cur.execute("UPDATE departments SET description = 'Updated in H2' WHERE id = %s;", (target_id,))
        assert cur.rowcount == 1, "Legitimate tenant UPDATE on own hospital record must succeed"

def test_rls_platform_admin_bypass(platform_conn, app_conn):
    """
    Verify aramis_platform has BYPASSRLS privilege and can see all tenant records
    without needing app.current_hospital_id set.
    """
    with platform_conn.cursor() as cur_plat:
        cur_plat.execute("SELECT current_user;")
        plat_user = cur_plat.fetchone()[0]
        assert plat_user == 'aramis_platform', f"Expected aramis_platform user, got {plat_user}"

        # Platform user queries departments across all hospitals without GUC
        cur_plat.execute("SELECT DISTINCT hospital_id FROM departments ORDER BY hospital_id;")
        hosp_ids = [row[0] for row in cur_plat.fetchall()]
        assert 1 in hosp_ids, "Platform admin must see Hospital 1 records"
        assert 2 in hosp_ids, "Platform admin must see Hospital 2 records"

        cur_plat.execute("SELECT count(*) FROM departments;")
        total_depts = cur_plat.fetchone()[0]

    # Verify that total count equals the sum of Hospital 1 + Hospital 2 counts from app_conn
    with app_conn.cursor() as cur_app:
        cur_app.execute("SET LOCAL app.current_hospital_id = '1';")
        cur_app.execute("SELECT count(*) FROM departments;")
        h1_count = cur_app.fetchone()[0]

        cur_app.execute("SET LOCAL app.current_hospital_id = '2';")
        cur_app.execute("SELECT count(*) FROM departments;")
        h2_count = cur_app.fetchone()[0]

    assert total_depts == h1_count + h2_count, f"Total platform count ({total_depts}) must equal sum of tenant counts ({h1_count} + {h2_count})"

def test_rls_appointments_cross_tenant_isolation(app_conn):
    """
    Verify clinical appointments isolation:
    H1 context cannot view or manipulate H2 appointments and vice versa.
    """
    with app_conn.cursor() as cur:
        # Check Hospital 1
        cur.execute("SET LOCAL app.current_hospital_id = '1';")
        cur.execute("SELECT id, hospital_id FROM appointments;")
        h1_appts = cur.fetchall()
        for appt_id, hosp_id in h1_appts:
            assert hosp_id == 1, f"Appointment {appt_id} in H1 context has invalid hospital_id {hosp_id}"

        # Attempt to modify any appointment belonging to hospital 2 while in H1 context
        cur.execute("UPDATE appointments SET notes = 'Hacked Notes' WHERE hospital_id = 2;")
        assert cur.rowcount == 0, f"Cannot update Hospital 2 appointments from Hospital 1 context (rows affected: {cur.rowcount})"

        # Check Hospital 2
        cur.execute("SET LOCAL app.current_hospital_id = '2';")
        cur.execute("SELECT id, hospital_id FROM appointments;")
        h2_appts = cur.fetchall()
        for appt_id, hosp_id in h2_appts:
            assert hosp_id == 2, f"Appointment {appt_id} in H2 context has invalid hospital_id {hosp_id}"

        # Attempt to modify any appointment belonging to hospital 1 while in H2 context
        cur.execute("UPDATE appointments SET notes = 'Hacked Notes' WHERE hospital_id = 1;")
        assert cur.rowcount == 0, f"Cannot update Hospital 1 appointments from Hospital 2 context (rows affected: {cur.rowcount})"

