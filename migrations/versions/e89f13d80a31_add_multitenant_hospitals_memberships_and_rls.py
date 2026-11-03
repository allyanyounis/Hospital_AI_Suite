"""add_multitenant_hospitals_memberships_and_rls

Revision ID: e89f13d80a31
Revises: a420c97a95ad
Create Date: 2026-11-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e89f13d80a31'
down_revision = 'a420c97a95ad'
branch_labels = None
depends_on = None

TENANT_TABLES = [
    'departments',
    'doctors',
    'appointments',
    'prescriptions',
    'medical_documents',
    'medical_histories',
    'refunds',
    'doctor_transactions',
    'doctor_payout_requests',
    'platform_revenues',
    'reviews',
    'blogs',
    'admin_audit_logs'
]

def upgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    # 1. Create hospitals table
    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('logo', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('settings', json_type, server_default='{"commission_percent": 20.0}', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('ix_hospitals_slug', 'hospitals', ['slug'], unique=True)
    op.create_index('ix_hospitals_city', 'hospitals', ['city'], unique=False)
    op.create_index('ix_hospitals_status', 'hospitals', ['status'], unique=False)

    # 2. Add hospital_id to departments before memberships (since memberships references departments)
    op.add_column('departments', sa.Column('hospital_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_departments_hospital_id', 'departments', 'hospitals', ['hospital_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_departments_hospital_id', 'departments', ['hospital_id'], unique=False)

    # Make department name/slug unique per hospital instead of globally
    if is_postgres:
        op.drop_index('ix_departments_name', table_name='departments')
        op.drop_index('ix_departments_slug', table_name='departments')
    op.create_index('uq_departments_hospital_slug', 'departments', ['hospital_id', 'slug'], unique=True)
    op.create_index('uq_departments_hospital_name', 'departments', ['hospital_id', 'name'], unique=True)

    # 3. Create hospital_memberships table
    op.create_table(
        'hospital_memberships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('reports_to_membership_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('time_slots', json_type, server_default='{}', nullable=True),
        sa.Column('consultation_fee_physical', sa.Float(), nullable=True),
        sa.Column('consultation_fee_video', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_hospital_memberships_user_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], name='fk_hospital_memberships_hospital_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_hospital_memberships_department_id', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reports_to_membership_id'], ['hospital_memberships.id'], name='fk_hospital_memberships_reports_to', ondelete='SET NULL')
    )
    op.create_index('ix_hospital_memberships_user_id', 'hospital_memberships', ['user_id'], unique=False)
    op.create_index('ix_hospital_memberships_hospital_id', 'hospital_memberships', ['hospital_id'], unique=False)
    op.create_index('ix_hospital_memberships_role', 'hospital_memberships', ['role'], unique=False)
    op.create_index('ix_hospital_memberships_dept', 'hospital_memberships', ['department_id'], unique=False)
    op.create_index('ix_hospital_memberships_hosp_role', 'hospital_memberships', ['hospital_id', 'role'], unique=False)
    op.create_index('uq_hospital_memberships_user_hosp_role_dept', 'hospital_memberships', ['user_id', 'hospital_id', 'role', 'department_id'], unique=True)

    # 4. Add hospital_id to remaining tenant tables
    other_tenant_tables = [
        'doctors',
        'appointments',
        'prescriptions',
        'medical_documents',
        'medical_histories',
        'refunds',
        'doctor_transactions',
        'doctor_payout_requests',
        'platform_revenues',
        'reviews',
        'blogs',
        'admin_audit_logs'
    ]

    for table in other_tenant_tables:
        op.add_column(table, sa.Column('hospital_id', sa.Integer(), nullable=True))
        on_del = 'SET NULL' if table in ('doctors', 'medical_documents', 'blogs', 'admin_audit_logs') else 'CASCADE'
        op.create_foreign_key(f'fk_{table}_hospital_id', table, 'hospitals', ['hospital_id'], ['id'], ondelete=on_del)
        op.create_index(f'ix_{table}_hospital_id', table, ['hospital_id'], unique=False)

    # 5. Enable Row-Level Security (RLS) on PostgreSQL
    if is_postgres:
        # Enable RLS on hospitals
        op.execute("ALTER TABLE hospitals ENABLE ROW LEVEL SECURITY;")
        op.execute("""
            CREATE POLICY tenant_hospitals_policy ON hospitals
            FOR ALL
            TO aramis_app
            USING (
                status = 'active'
                OR id = NULLIF(current_setting('app.current_hospital_id', true), '')::integer
            );
        """)

        # Enable RLS on hospital_memberships
        op.execute("ALTER TABLE hospital_memberships ENABLE ROW LEVEL SECURITY;")
        op.execute("""
            CREATE POLICY tenant_memberships_policy ON hospital_memberships
            FOR ALL
            TO aramis_app
            USING (
                hospital_id = NULLIF(current_setting('app.current_hospital_id', true), '')::integer
                OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
            );
        """)

        # Enable RLS on each tenant-scoped table
        for table in TENANT_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"""
                CREATE POLICY tenant_isolation_policy ON {table}
                FOR ALL
                TO aramis_app
                USING (
                    hospital_id = NULLIF(current_setting('app.current_hospital_id', true), '')::integer
                );
            """)

        # Re-grant table and sequence privileges to aramis_app and aramis_platform
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO aramis_app, aramis_platform;")
        op.execute("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO aramis_app, aramis_platform;")


def downgrade():
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    if is_postgres:
        for table in TENANT_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute("DROP POLICY IF EXISTS tenant_memberships_policy ON hospital_memberships;")
        op.execute("ALTER TABLE hospital_memberships DISABLE ROW LEVEL SECURITY;")
        op.execute("DROP POLICY IF EXISTS tenant_hospitals_policy ON hospitals;")
        op.execute("ALTER TABLE hospitals DISABLE ROW LEVEL SECURITY;")

    other_tenant_tables = [
        'admin_audit_logs',
        'blogs',
        'reviews',
        'platform_revenues',
        'doctor_payout_requests',
        'doctor_transactions',
        'refunds',
        'medical_histories',
        'medical_documents',
        'prescriptions',
        'appointments',
        'doctors'
    ]

    for table in other_tenant_tables:
        op.drop_constraint(f'fk_{table}_hospital_id', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_hospital_id', table_name=table)
        op.drop_column(table, 'hospital_id')

    op.drop_table('hospital_memberships')

    op.drop_index('uq_departments_hospital_name', table_name='departments')
    op.drop_index('uq_departments_hospital_slug', table_name='departments')
    op.drop_index('ix_departments_hospital_id', table_name='departments')
    op.drop_constraint('fk_departments_hospital_id', 'departments', type_='foreignkey')
    op.drop_column('departments', 'hospital_id')

    if is_postgres:
        op.create_index('ix_departments_slug', 'departments', ['slug'], unique=True)
        op.create_index('ix_departments_name', 'departments', ['name'], unique=True)

    op.drop_table('hospitals')

