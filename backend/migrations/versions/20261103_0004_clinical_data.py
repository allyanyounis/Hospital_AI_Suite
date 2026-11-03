"""Clinical data: the lab test catalogue, lab results, vital signs, reports, history and allergies of a patient.

The catalogue starts with the nine tests the theatre list and its risk score read (ranges from the POC seed).

Revision ID: 0004
Revises: 0003
Created: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LAB_TESTS = [
    ("HGB", "Haemoglobin", "g/dL", 12.0, 16.0, "haematology"),
    ("WBC", "White cells", "10^9/L", 4.0, 11.0, "haematology"),
    ("PLT", "Platelets", "10^9/L", 150, 400, "haematology"),
    ("NA", "Sodium", "mmol/L", 135, 145, "chemistry"),
    ("K", "Potassium", "mmol/L", 3.5, 5.1, "chemistry"),
    ("CREA", "Creatinine", "mg/dL", 0.6, 1.2, "chemistry"),
    ("GLU", "Glucose", "mg/dL", 70, 140, "chemistry"),
    ("ALB", "Albumin", "g/dL", 3.5, 5.0, "chemistry"),
    ("INR", "INR", "", 0.8, 1.2, "coagulation"),
]


def upgrade() -> None:
    op.create_table(
        "lab_tests",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=30), server_default="", nullable=False),
        sa.Column("ref_low", sa.Float(), nullable=False),
        sa.Column("ref_high", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint(
            "category IN ('haematology', 'chemistry', 'coagulation')", name=op.f("ck_lab_tests_category")
        ),
        sa.CheckConstraint("ref_high > ref_low", name=op.f("ck_lab_tests_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_tests")),
        sa.UniqueConstraint("code", name=op.f("uq_lab_tests_code")),
    )
    op.create_table(
        "clinical_history",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("noted_on", sa.Date(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('indication', 'condition', 'surgery')", name=op.f("ck_clinical_history_kind")),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_clinical_history_patient_id_patients"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_history")),
    )
    op.create_index("ix_clinical_history_patient_noted", "clinical_history", ["patient_id", "noted_on"], unique=False)
    op.create_table(
        "clinical_reports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("reported_on", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=10), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('ultrasound', 'ecg', 'xray', 'ct', 'mri', 'echo', 'angiogram', 'mammography', 'pathology', "
            "'anaesthesia_review', 'other')",
            name=op.f("ck_clinical_reports_kind"),
        ),
        sa.CheckConstraint("source IN ('seed', 'manual', 'import')", name=op.f("ck_clinical_reports_source")),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_clinical_reports_patient_id_patients"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_reports")),
    )
    op.create_index("ix_clinical_reports_patient_kind", "clinical_reports", ["patient_id", "kind"], unique=False)
    op.create_index(
        "ix_clinical_reports_patient_reported", "clinical_reports", ["patient_id", "reported_on"], unique=False
    )
    op.create_table(
        "patient_allergies",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("substance", sa.String(length=120), nullable=False),
        sa.Column("reaction", sa.String(length=120), nullable=True),
        sa.Column("severity", sa.String(length=10), server_default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "severity IN ('mild', 'moderate', 'severe', 'unknown')", name=op.f("ck_patient_allergies_severity")
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_patient_allergies_patient_id_patients"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_allergies")),
    )
    op.create_index(op.f("ix_patient_allergies_patient_id"), "patient_allergies", ["patient_id"], unique=False)
    op.create_table(
        "lab_results",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("flag", sa.String(length=10), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=10), server_default="manual", nullable=False),
        sa.Column("entered_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("flag IN ('low', 'normal', 'high')", name=op.f("ck_lab_results_flag")),
        sa.CheckConstraint("source IN ('seed', 'manual', 'import')", name=op.f("ck_lab_results_source")),
        sa.ForeignKeyConstraint(["entered_by"], ["users.username"], name=op.f("fk_lab_results_entered_by_users")),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_lab_results_patient_id_patients"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["test_id"], ["lab_tests.id"], name=op.f("fk_lab_results_test_id_lab_tests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lab_results")),
    )
    op.create_index("ix_lab_results_patient_collected", "lab_results", ["patient_id", "collected_at"], unique=False)
    op.create_index(
        "ix_lab_results_patient_test_collected", "lab_results", ["patient_id", "test_id", "collected_at"], unique=False
    )
    op.create_table(
        "vital_signs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("spo2", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("resp_rate", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=10), server_default="manual", nullable=False),
        sa.Column("recorded_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source IN ('seed', 'manual', 'import')", name=op.f("ck_vital_signs_source")),
        sa.CheckConstraint("diastolic_bp BETWEEN 20 AND 200", name=op.f("ck_vital_signs_diastolic_bp")),
        sa.CheckConstraint("heart_rate BETWEEN 20 AND 300", name=op.f("ck_vital_signs_heart_rate")),
        sa.CheckConstraint("resp_rate BETWEEN 2 AND 80", name=op.f("ck_vital_signs_resp_rate")),
        sa.CheckConstraint("spo2 BETWEEN 50 AND 100", name=op.f("ck_vital_signs_spo2")),
        sa.CheckConstraint("systolic_bp BETWEEN 40 AND 300", name=op.f("ck_vital_signs_systolic_bp")),
        sa.CheckConstraint("temperature_c BETWEEN 30 AND 45", name=op.f("ck_vital_signs_temperature_c")),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_vital_signs_patient_id_patients"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.username"], name=op.f("fk_vital_signs_recorded_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vital_signs")),
    )
    op.create_index("ix_vital_signs_patient_recorded", "vital_signs", ["patient_id", "recorded_at"], unique=False)

    lab_tests = sa.table(
        "lab_tests",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("unit", sa.String),
        sa.column("ref_low", sa.Float),
        sa.column("ref_high", sa.Float),
        sa.column("category", sa.String),
    )
    op.bulk_insert(
        lab_tests,
        [dict(zip(("code", "name", "unit", "ref_low", "ref_high", "category"), row, strict=True)) for row in LAB_TESTS],
    )


def downgrade() -> None:
    op.drop_index("ix_vital_signs_patient_recorded", table_name="vital_signs")
    op.drop_table("vital_signs")
    op.drop_index("ix_lab_results_patient_test_collected", table_name="lab_results")
    op.drop_index("ix_lab_results_patient_collected", table_name="lab_results")
    op.drop_table("lab_results")
    op.drop_index(op.f("ix_patient_allergies_patient_id"), table_name="patient_allergies")
    op.drop_table("patient_allergies")
    op.drop_index("ix_clinical_reports_patient_reported", table_name="clinical_reports")
    op.drop_index("ix_clinical_reports_patient_kind", table_name="clinical_reports")
    op.drop_table("clinical_reports")
    op.drop_index("ix_clinical_history_patient_noted", table_name="clinical_history")
    op.drop_table("clinical_history")
    op.drop_table("lab_tests")
