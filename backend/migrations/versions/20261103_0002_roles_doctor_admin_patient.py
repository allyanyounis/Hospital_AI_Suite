"""Roles become admin / doctor / patient; patient accounts link to a patient; sessions carry a version.

- users.role: 'clinician' is renamed 'doctor' (existing rows are converted), 'patient' is added.
- users.patient_id: the patient record a patient account belongs to (unique; required exactly for patients).
- users.session_version: part of every session token; bumped to sign a user out everywhere.
- clinic_settings.id: drop the sequence default it never needed (single row, id = 1).

Revision ID: 0002
Revises: 0001
Created: 2026-11-03 13:05:56.792649
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("clinic_settings", "id", existing_type=sa.SMALLINT(), server_default=None, existing_nullable=False)
    op.execute("DROP SEQUENCE IF EXISTS clinic_settings_id_seq")

    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.execute("UPDATE users SET role = 'doctor' WHERE role = 'clinician'")
    op.alter_column("users", "role", existing_type=sa.VARCHAR(length=20), server_default="doctor")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('admin', 'doctor', 'patient')")

    op.add_column("users", sa.Column("patient_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("session_version", sa.Integer(), server_default="1", nullable=False))
    op.create_unique_constraint(op.f("uq_users_patient_id"), "users", ["patient_id"])
    op.create_foreign_key(op.f("fk_users_patient_id_patients"), "users", "patients", ["patient_id"], ["id"])
    op.create_check_constraint(op.f("ck_users_patient_link"), "users", "(role = 'patient') = (patient_id IS NOT NULL)")


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE role = 'patient'")
    op.drop_constraint(op.f("ck_users_patient_link"), "users", type_="check")
    op.drop_constraint(op.f("fk_users_patient_id_patients"), "users", type_="foreignkey")
    op.drop_constraint(op.f("uq_users_patient_id"), "users", type_="unique")
    op.drop_column("users", "session_version")
    op.drop_column("users", "patient_id")

    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.execute("UPDATE users SET role = 'clinician' WHERE role = 'doctor'")
    op.alter_column("users", "role", existing_type=sa.VARCHAR(length=20), server_default="clinician")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('clinician', 'admin')")
