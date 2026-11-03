"""Operating theatres: theatres, procedures, surgical cases with their pre-op assessments, surgeons' theatre
sessions and leave. Empty: the demo list comes from `python -m app seed demo-theatre`.

Revision ID: 0005
Revises: 0004
Created: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "procedures",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("specialty", sa.String(length=60), nullable=False),
        sa.Column("induction", sa.SmallInteger(), nullable=False),
        sa.Column("lead_in", sa.SmallInteger(), nullable=False),
        sa.Column("incision", sa.SmallInteger(), nullable=False),
        sa.Column("lead_out", sa.SmallInteger(), nullable=False),
        sa.Column("emergence", sa.SmallInteger(), nullable=False),
        sa.Column("variance", sa.Float(), nullable=False),
        sa.Column("risk_model", sa.String(length=12), server_default="vitaldb", nullable=False),
        sa.Column("euro_weight", sa.SmallInteger(), nullable=True),
        sa.Column("aorta", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.Text(), server_default="", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("risk_model IN ('vitaldb', 'euroscore2')", name=op.f("ck_procedures_risk_model")),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_procedures")),
    )
    op.create_table(
        "theatres",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("specialty", sa.String(length=60), nullable=False),
        sa.Column("cleaning_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name=op.f("fk_theatres_department_id_departments")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_theatres")),
        sa.UniqueConstraint("code", name=op.f("uq_theatres_code")),
    )
    op.create_index(op.f("ix_theatres_department_id"), "theatres", ["department_id"], unique=False)
    op.create_table(
        "staff_leave",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=120), server_default="Leave", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("ends_on >= starts_on", name=op.f("ck_staff_leave_ends_after_starts")),
        sa.ForeignKeyConstraint(
            ["staff_id"], ["staff_members.id"], name=op.f("fk_staff_leave_staff_id_staff_members"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_leave")),
    )
    op.create_index(op.f("ix_staff_leave_staff_id"), "staff_leave", ["staff_id"], unique=False)
    op.create_table(
        "surgical_cases",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("procedure_code", sa.String(length=16), nullable=False),
        sa.Column("theatre_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_on", sa.Date(), nullable=True),
        sa.Column("seq", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("urgency", sa.String(length=10), server_default="elective", nullable=False),
        sa.Column("surgeon_id", sa.Integer(), nullable=True),
        sa.Column("overrun_minutes", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("deferred", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canceled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "urgency IN ('immediate', 'urgent', 'expedited', 'elective')", name=op.f("ck_surgical_cases_urgency")
        ),
        sa.CheckConstraint("overrun_minutes >= 0", name=op.f("ck_surgical_cases_overrun_minutes")),
        sa.ForeignKeyConstraint(["created_by"], ["users.username"], name=op.f("fk_surgical_cases_created_by_users")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_surgical_cases_patient_id_patients")),
        sa.ForeignKeyConstraint(
            ["procedure_code"], ["procedures.code"], name=op.f("fk_surgical_cases_procedure_code_procedures")
        ),
        sa.ForeignKeyConstraint(
            ["surgeon_id"], ["staff_members.id"], name=op.f("fk_surgical_cases_surgeon_id_staff_members")
        ),
        sa.ForeignKeyConstraint(["theatre_id"], ["theatres.id"], name=op.f("fk_surgical_cases_theatre_id_theatres")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_surgical_cases")),
    )
    op.create_index(op.f("ix_surgical_cases_patient_id"), "surgical_cases", ["patient_id"], unique=False)
    op.create_index(
        "ix_surgical_cases_scheduled_on_theatre_id", "surgical_cases", ["scheduled_on", "theatre_id"], unique=False
    )
    op.create_index(op.f("ix_surgical_cases_surgeon_id"), "surgical_cases", ["surgeon_id"], unique=False)
    op.create_table(
        "theatre_rosters",
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("starts", sa.Time(), nullable=False),
        sa.Column("ends", sa.Time(), nullable=False),
        sa.CheckConstraint("ends > starts", name=op.f("ck_theatre_rosters_ends_after_starts")),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_theatre_rosters_weekday")),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_members.id"],
            name=op.f("fk_theatre_rosters_staff_id_staff_members"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("staff_id", "weekday", name=op.f("pk_theatre_rosters")),
    )
    op.create_table(
        "preop_assessments",
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("asa", sa.SmallInteger(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("lvef", sa.SmallInteger(), nullable=True),
        sa.Column("nyha", sa.SmallInteger(), nullable=True),
        sa.Column("pa_systolic", sa.SmallInteger(), nullable=True),
        sa.Column("ccs4", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("iddm", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recent_mi", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("redo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("lung", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("arteriopathy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("poor_mobility", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dialysis", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("endocarditis", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("critical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("asa BETWEEN 1 AND 6", name=op.f("ck_preop_assessments_asa")),
        sa.CheckConstraint("lvef BETWEEN 5 AND 90", name=op.f("ck_preop_assessments_lvef")),
        sa.CheckConstraint("nyha BETWEEN 1 AND 4", name=op.f("ck_preop_assessments_nyha")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["surgical_cases.id"],
            name=op.f("fk_preop_assessments_case_id_surgical_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("case_id", name=op.f("pk_preop_assessments")),
    )


def downgrade() -> None:
    op.drop_table("preop_assessments")
    op.drop_table("theatre_rosters")
    op.drop_index(op.f("ix_surgical_cases_surgeon_id"), table_name="surgical_cases")
    op.drop_index("ix_surgical_cases_scheduled_on_theatre_id", table_name="surgical_cases")
    op.drop_index(op.f("ix_surgical_cases_patient_id"), table_name="surgical_cases")
    op.drop_table("surgical_cases")
    op.drop_index(op.f("ix_staff_leave_staff_id"), table_name="staff_leave")
    op.drop_table("staff_leave")
    op.drop_index(op.f("ix_theatres_department_id"), table_name="theatres")
    op.drop_table("theatres")
    op.drop_table("procedures")
