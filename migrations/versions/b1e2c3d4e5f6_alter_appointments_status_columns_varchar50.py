"""alter_appointments_status_columns_varchar50

Revision ID: b1e2c3d4e5f6
Revises: e89f13d80a31
Create Date: 2026-11-03 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1e2c3d4e5f6'
down_revision = 'e89f13d80a31'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=20),
            type_=sa.String(length=50),
            existing_nullable=True
        )
        batch_op.alter_column(
            'payment_status',
            existing_type=sa.String(length=20),
            type_=sa.String(length=50),
            existing_nullable=True
        )


def downgrade():
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.alter_column(
            'payment_status',
            existing_type=sa.String(length=50),
            type_=sa.String(length=20),
            existing_nullable=True
        )
        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=50),
            type_=sa.String(length=20),
            existing_nullable=True
        )
