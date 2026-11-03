"""Hospital foundation: departments, staff profiles, per-doctor OPD schedules, doctor on every appointment,
voice-call links owned by the receptionist, patient contact details, nurse and receptionist roles.

Data carried over:
- every admin/doctor account gets a bookable staff profile in a new "General Medicine" (GEN) department;
- the saved clinic schedule becomes each of those doctors' schedule; clinic closures become hospital closures;
- existing appointments go to the first doctor (by account creation) and are marked booked_via = 'voice';
- appointments.call_id rows move to voice_call_bookings;
- patients with a portal account are marked registered (permanent records).

Revision ID: 0003
Revises: 0002
Created: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Roles -----------------------------------------------------------------------------------------------------
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"), "users", "role IN ('admin', 'doctor', 'nurse', 'receptionist', 'patient')"
    )

    # --- Patients: contact details and registration ---------------------------------------------------------------
    op.add_column("patients", sa.Column("phone", sa.String(length=30), nullable=True))
    op.add_column("patients", sa.Column("email", sa.String(length=254), nullable=True))
    op.add_column("patients", sa.Column("registered", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_index(op.f("ix_patients_phone"), "patients", ["phone"])
    op.execute(
        "UPDATE patients SET registered = true WHERE id IN (SELECT patient_id FROM users WHERE patient_id IS NOT NULL)"
    )

    # --- Organisation and staff -----------------------------------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=20), server_default="clinical", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("code ~ '^[A-Z0-9_-]{2,16}$'", name=op.f("ck_departments_code_format")),
        sa.CheckConstraint(
            "kind IN ('clinical', 'diagnostic', 'support', 'administrative')", name=op.f("ck_departments_kind")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    op.create_table(
        "staff_members",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("specialty", sa.String(length=120), nullable=True),
        sa.Column("registration_number", sa.String(length=60), nullable=True),
        sa.Column("bookable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name=op.f("fk_staff_members_department_id_departments")
        ),
        sa.ForeignKeyConstraint(["username"], ["users.username"], name=op.f("fk_staff_members_username_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_members")),
        sa.UniqueConstraint("registration_number", name=op.f("uq_staff_members_registration_number")),
        sa.UniqueConstraint("username", name=op.f("uq_staff_members_username")),
    )
    op.create_index(op.f("ix_staff_members_department_id"), "staff_members", ["department_id"])
    op.execute("INSERT INTO departments (code, name, kind) VALUES ('GEN', 'General Medicine', 'clinical')")
    op.execute(
        "INSERT INTO staff_members (username, department_id, job_title, bookable) "
        "SELECT u.username, d.id, 'Doctor', true FROM users u, departments d "
        "WHERE d.code = 'GEN' AND u.role IN ('admin', 'doctor') ORDER BY u.created_at"
    )

    # --- Scheduling: per doctor -----------------------------------------------------------------------------------
    op.create_table(
        "doctor_schedules",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("slot_minutes", sa.SmallInteger(), server_default="15", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.CheckConstraint("slot_minutes BETWEEN 5 AND 120", name=op.f("ck_doctor_schedules_slot_minutes")),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_members.id"],
            name=op.f("fk_doctor_schedules_staff_id_staff_members"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.username"], name=op.f("fk_doctor_schedules_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_doctor_schedules")),
        sa.UniqueConstraint("staff_id", name=op.f("uq_doctor_schedules_staff_id")),
    )
    op.create_table(
        "schedule_days",
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("opens", sa.Time(), nullable=False),
        sa.Column("closes", sa.Time(), nullable=False),
        sa.CheckConstraint("NOT enabled OR closes > opens", name=op.f("ck_schedule_days_closes_after_opens")),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name=op.f("ck_schedule_days_weekday")),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["doctor_schedules.id"],
            name=op.f("fk_schedule_days_schedule_id_doctor_schedules"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("schedule_id", "weekday", name=op.f("pk_schedule_days")),
    )
    op.create_table(
        "schedule_breaks",
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("starts", sa.Time(), nullable=False),
        sa.Column("ends", sa.Time(), nullable=False),
        sa.CheckConstraint("ends > starts", name=op.f("ck_schedule_breaks_ends_after_starts")),
        sa.ForeignKeyConstraint(
            ["schedule_id", "weekday"],
            ["schedule_days.schedule_id", "schedule_days.weekday"],
            name=op.f("fk_schedule_breaks_day"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("schedule_id", "weekday", "starts", name=op.f("pk_schedule_breaks")),
    )
    # The clinic's saved week becomes every existing doctor's week
    op.execute(
        "INSERT INTO doctor_schedules (staff_id, slot_minutes, updated_at, updated_by) "
        "SELECT s.id, c.slot_minutes, c.updated_at, c.updated_by FROM staff_members s CROSS JOIN clinic_settings c "
        "WHERE s.bookable"
    )
    op.execute(
        "INSERT INTO schedule_days (schedule_id, weekday, enabled, opens, closes) "
        "SELECT ds.id, h.weekday, h.enabled, h.opens, h.closes FROM doctor_schedules ds CROSS JOIN clinic_hours h"
    )
    op.execute(
        "INSERT INTO schedule_breaks (schedule_id, weekday, starts, ends) "
        "SELECT ds.id, b.weekday, b.starts, b.ends FROM doctor_schedules ds CROSS JOIN clinic_breaks b"
    )
    op.rename_table("clinic_closures", "hospital_closures")
    op.execute("ALTER TABLE hospital_closures RENAME CONSTRAINT pk_clinic_closures TO pk_hospital_closures")
    op.add_column("hospital_closures", sa.Column("reason", sa.String(length=120), nullable=True))
    op.drop_table("clinic_breaks")
    op.drop_table("clinic_hours")
    op.drop_table("clinic_settings")

    # --- Appointments: a doctor on every appointment; the booking channel --------------------------------------------
    op.add_column("appointments", sa.Column("practitioner_id", sa.Integer(), nullable=True))
    op.add_column("appointments", sa.Column("booked_via", sa.String(length=10), nullable=True))
    op.execute(
        "UPDATE appointments SET booked_via = 'voice', practitioner_id = "
        "(SELECT s.id FROM staff_members s JOIN users u ON u.username = s.username WHERE s.bookable "
        "ORDER BY u.created_at LIMIT 1)"
    )
    orphans = op.get_bind().scalar(sa.text("SELECT count(*) FROM appointments WHERE practitioner_id IS NULL"))
    if orphans:
        raise RuntimeError(
            f"{orphans} appointments but no doctor account to assign them to. Create a doctor account "
            "(python -m app users add … --role doctor) on the previous version, then migrate again."
        )
    op.alter_column("appointments", "practitioner_id", nullable=False)
    op.alter_column("appointments", "booked_via", nullable=False)
    op.create_check_constraint(
        op.f("ck_appointments_booked_via"), "appointments", "booked_via IN ('voice', 'desk', 'portal')"
    )
    op.create_foreign_key(
        op.f("fk_appointments_practitioner_id_staff_members"),
        "appointments",
        "staff_members",
        ["practitioner_id"],
        ["id"],
    )
    op.create_index(op.f("ix_appointments_practitioner_id"), "appointments", ["practitioner_id"])
    op.drop_index("uq_appointments_active_slot", table_name="appointments")
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["practitioner_id", "start_time"],
        unique=True,
        postgresql_where=sa.text("NOT canceled"),
    )

    # --- Voice calls: the receptionist owns the call <-> appointment link --------------------------------------------
    op.create_table(
        "voice_call_bookings",
        sa.Column("call_id", sa.String(length=64), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f("fk_voice_call_bookings_appointment_id_appointments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["call_id"], ["voice_calls.id"], name=op.f("fk_voice_call_bookings_call_id_voice_calls"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("call_id", "appointment_id", name=op.f("pk_voice_call_bookings")),
        sa.UniqueConstraint("appointment_id", name=op.f("uq_voice_call_bookings_appointment_id")),
    )
    op.execute(
        "INSERT INTO voice_call_bookings (call_id, appointment_id) "
        "SELECT call_id, id FROM appointments WHERE call_id IS NOT NULL"
    )
    op.drop_index("ix_appointments_call_id", table_name="appointments")
    op.drop_constraint(op.f("fk_appointments_call_id_voice_calls"), "appointments", type_="foreignkey")
    op.drop_column("appointments", "call_id")


def downgrade() -> None:
    # Appointments: back to one clinic, the voice link on the row
    op.add_column("appointments", sa.Column("call_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE appointments a SET call_id = v.call_id FROM voice_call_bookings v WHERE v.appointment_id = a.id")
    op.create_foreign_key(
        op.f("fk_appointments_call_id_voice_calls"), "appointments", "voice_calls", ["call_id"], ["id"]
    )
    op.create_index("ix_appointments_call_id", "appointments", ["call_id"])
    op.drop_table("voice_call_bookings")
    op.drop_index("uq_appointments_active_slot", table_name="appointments")
    op.execute(  # one clinic: keep the earliest active booking per start time, cancel the rest
        "UPDATE appointments a SET canceled = true WHERE NOT a.canceled AND EXISTS (SELECT 1 FROM appointments b "
        "WHERE NOT b.canceled AND b.start_time = a.start_time AND b.id < a.id)"
    )
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["start_time"],
        unique=True,
        postgresql_where=sa.text("NOT canceled"),
    )
    op.drop_index(op.f("ix_appointments_practitioner_id"), table_name="appointments")
    op.drop_constraint(op.f("fk_appointments_practitioner_id_staff_members"), "appointments", type_="foreignkey")
    op.drop_constraint(op.f("ck_appointments_booked_via"), "appointments", type_="check")
    op.drop_column("appointments", "booked_via")
    op.drop_column("appointments", "practitioner_id")

    # Scheduling: the first doctor's week becomes the clinic's
    op.create_table(
        "clinic_settings",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("slot_minutes", sa.SmallInteger(), server_default="15", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.CheckConstraint("id = 1", name=op.f("ck_clinic_settings_single_row")),
        sa.CheckConstraint("slot_minutes BETWEEN 5 AND 120", name=op.f("ck_clinic_settings_slot_minutes")),
        sa.ForeignKeyConstraint(["updated_by"], ["users.username"], name=op.f("fk_clinic_settings_updated_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinic_settings")),
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
    first = "(SELECT id FROM doctor_schedules ORDER BY id LIMIT 1)"
    op.execute(
        "INSERT INTO clinic_settings (id, slot_minutes, updated_at, updated_by) "
        f"SELECT 1, slot_minutes, updated_at, updated_by FROM doctor_schedules WHERE id = {first}"
    )
    op.execute(
        "INSERT INTO clinic_hours (weekday, enabled, opens, closes) "
        f"SELECT weekday, enabled, opens, closes FROM schedule_days WHERE schedule_id = {first}"
    )
    op.execute(
        "INSERT INTO clinic_breaks (weekday, starts, ends) "
        f"SELECT weekday, starts, ends FROM schedule_breaks WHERE schedule_id = {first}"
    )
    op.drop_column("hospital_closures", "reason")
    op.execute("ALTER TABLE hospital_closures RENAME CONSTRAINT pk_hospital_closures TO pk_clinic_closures")
    op.rename_table("hospital_closures", "clinic_closures")
    op.drop_table("schedule_breaks")
    op.drop_table("schedule_days")
    op.drop_table("doctor_schedules")

    # Organisation and staff
    op.drop_index(op.f("ix_staff_members_department_id"), table_name="staff_members")
    op.drop_table("staff_members")
    op.drop_table("departments")

    # Patients and roles
    op.drop_index(op.f("ix_patients_phone"), table_name="patients")
    op.drop_column("patients", "registered")
    op.drop_column("patients", "email")
    op.drop_column("patients", "phone")
    op.execute("DELETE FROM users WHERE role IN ('nurse', 'receptionist')")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('admin', 'doctor', 'patient')")
