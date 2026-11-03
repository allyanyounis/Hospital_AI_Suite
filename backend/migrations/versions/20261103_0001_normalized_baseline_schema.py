"""Normalized baseline schema (3NF): patients, voice calls, clinic hours/breaks/closures, encounter codes/tasks.

Replaces the earlier create_all() schema; see docs/database.md.

Revision ID: 0001
Revises:
Created: 2026-11-03 12:25:55.955894
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clinic_closures",
        sa.Column("closed_on", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("closed_on", name=op.f("pk_clinic_closures")),
    )
    op.create_table(
        "clinic_hours",
        sa.Column("weekday", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("opens", sa.Time(), nullable=False),
        sa.Column("closes", sa.Time(), nullable=False),
        sa.CheckConstraint("NOT enabled OR closes > opens", name=op.f("ck_clinic_hours_closes_after_opens")),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_clinic_hours_weekday")),
        sa.PrimaryKeyConstraint("weekday", name=op.f("pk_clinic_hours")),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("mrn", sa.String(length=60), nullable=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("sex", sa.String(length=30), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("btrim(full_name) <> ''", name=op.f("ck_patients_full_name_not_blank")),
        sa.CheckConstraint("sex IN ('Female', 'Male', 'Other', 'Not stated')", name=op.f("ck_patients_sex")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
        sa.UniqueConstraint("mrn", name=op.f("uq_patients_mrn")),
    )
    op.create_index("ix_patients_full_name_lower", "patients", [sa.literal_column("lower(full_name)")], unique=False)
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="clinician", nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('clinician', 'admin')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("username", name=op.f("pk_users")),
    )
    op.create_table(
        "voice_calls",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_calls")),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("call_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], name=op.f("fk_appointments_call_id_voice_calls")),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name=op.f("fk_appointments_patient_id_patients")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
    )
    op.create_index("ix_appointments_call_id", "appointments", ["call_id"], unique=False)
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"], unique=False)
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"], unique=False)
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["start_time"],
        unique=True,
        postgresql_where=sa.text("NOT canceled"),
    )
    op.create_table(
        "clinic_breaks",
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("starts", sa.Time(), nullable=False),
        sa.Column("ends", sa.Time(), nullable=False),
        sa.CheckConstraint("ends > starts", name=op.f("ck_clinic_breaks_ends_after_starts")),
        sa.ForeignKeyConstraint(
            ["weekday"],
            ["clinic_hours.weekday"],
            name=op.f("fk_clinic_breaks_weekday_clinic_hours"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("weekday", "starts", name=op.f("pk_clinic_breaks")),
    )
    op.create_table(
        "clinic_settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("slot_minutes", sa.SmallInteger(), server_default="15", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.CheckConstraint("id = 1", name=op.f("ck_clinic_settings_single_row")),
        sa.CheckConstraint("slot_minutes BETWEEN 5 AND 120", name=op.f("ck_clinic_settings_slot_minutes")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.username"], name=op.f("fk_clinic_settings_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinic_settings")),
    )
    op.create_table(
        "encounters",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("audio_seconds", sa.Float(), nullable=True),
        sa.Column("transcript", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("clinician_speaker", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=True),
        sa.Column("visit_type", sa.String(length=60), nullable=True),
        sa.Column("template_id", sa.String(length=64), nullable=True),
        sa.Column("note_status", sa.String(length=20), nullable=True),
        sa.Column("note_error", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("draft_note", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("draft_seconds", sa.Float(), nullable=True),
        sa.Column("drafted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_note", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("codes_source", sa.String(length=10), nullable=True),
        sa.Column("codes_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tasks_source", sa.String(length=10), nullable=True),
        sa.Column("tasks_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lines_drafted", sa.Integer(), nullable=True),
        sa.Column("lines_kept", sa.Integer(), nullable=True),
        sa.Column("lines_added", sa.Integer(), nullable=True),
        sa.Column("lines_removed", sa.Integer(), nullable=True),
        sa.Column("content_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("codes_source IN ('draft', 'signed')", name=op.f("ck_encounters_codes_source")),
        sa.CheckConstraint("note_status IN ('drafting', 'ready', 'failed')", name=op.f("ck_encounters_note_status")),
        sa.CheckConstraint("source IN ('live', 'recording', 'sample')", name=op.f("ck_encounters_source")),
        sa.CheckConstraint("tasks_source IN ('draft', 'signed')", name=op.f("ck_encounters_tasks_source")),
        sa.CheckConstraint(
            "approved_at IS NULL OR drafted_at IS NOT NULL", name=op.f("ck_encounters_approved_after_drafted")
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_encounters_patient_id_patients"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["username"], ["users.username"], name=op.f("fk_encounters_username_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_encounters")),
    )
    op.create_index("ix_encounters_patient_id", "encounters", ["patient_id"], unique=False)
    op.create_index("ix_encounters_username_created_at", "encounters", ["username", "created_at"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("encounter_id", sa.String(length=32), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], name=op.f("fk_audit_log_encounter_id_encounters")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index("ix_audit_log_encounter_id", "audit_log", ["encounter_id"], unique=False)
    op.create_index("ix_audit_log_username_ts", "audit_log", ["username", "ts"], unique=False)
    op.create_table(
        "encounter_codes",
        sa.Column("encounter_id", sa.String(length=32), nullable=False),
        sa.Column("position", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.String(length=10), nullable=False),
        sa.Column("evidence", sa.Text(), server_default="", nullable=False),
        sa.CheckConstraint("confidence IN ('high', 'medium', 'low')", name=op.f("ck_encounter_codes_confidence")),
        sa.CheckConstraint(
            "kind IN ('primary', 'secondary', 'symptom', 'history')", name=op.f("ck_encounter_codes_kind")
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_encounter_codes_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("encounter_id", "position", name=op.f("pk_encounter_codes")),
    )
    op.create_table(
        "encounter_tasks",
        sa.Column("encounter_id", sa.String(length=32), nullable=False),
        sa.Column("position", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), server_default="", nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("owner", sa.String(length=10), nullable=False),
        sa.Column("due", sa.String(length=120), server_default="", nullable=False),
        sa.Column("done", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "category IN ('test', 'medication', 'referral', 'follow_up', 'patient_advice', 'admin')",
            name=op.f("ck_encounter_tasks_category"),
        ),
        sa.CheckConstraint(
            "owner IN ('clinician', 'nurse', 'patient', 'admin')", name=op.f("ck_encounter_tasks_owner")
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_encounter_tasks_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("encounter_id", "position", name=op.f("pk_encounter_tasks")),
    )


def downgrade() -> None:
    op.drop_table("encounter_tasks")
    op.drop_table("encounter_codes")
    op.drop_index("ix_audit_log_username_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_encounter_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_encounters_username_created_at", table_name="encounters")
    op.drop_index("ix_encounters_patient_id", table_name="encounters")
    op.drop_table("encounters")
    op.drop_table("clinic_settings")
    op.drop_table("clinic_breaks")
    op.drop_index("uq_appointments_active_slot", table_name="appointments", postgresql_where=sa.text("NOT canceled"))
    op.drop_index("ix_appointments_start_time", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_index("ix_appointments_call_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("voice_calls")
    op.drop_table("users")
    op.drop_index("ix_patients_full_name_lower", table_name="patients")
    op.drop_table("patients")
    op.drop_table("clinic_hours")
    op.drop_table("clinic_closures")
