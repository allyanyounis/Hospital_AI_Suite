"""Registry of every table. Each module owns its models; importing this module registers them all on
Base.metadata (used by Alembic migrations and the tests). A new module's models are imported here.
Schema and diagrams: docs/database.md.

Two kinds of JSONB remain on purpose: the transcript and note documents (written and read whole, never queried
inside, cited by segment id) and the audit log's free-form `detail`. Everything the app edits row by row is a table.
"""

from app.core.audit import AuditLog
from app.modules.appointments.models import Appointment
from app.modules.auth.models import User
from app.modules.clinical.models import (
    ClinicalHistory,
    ClinicalReport,
    LabResult,
    LabTest,
    PatientAllergy,
    VitalSigns,
)
from app.modules.organization.models import Department
from app.modules.patients.models import Patient
from app.modules.reception.models import VoiceCall, VoiceCallBooking
from app.modules.scheduling.models import DoctorSchedule, HospitalClosure, ScheduleBreak, ScheduleDay
from app.modules.scribe.models import Encounter, EncounterCode, EncounterTask
from app.modules.staff.models import StaffMember
from app.modules.theatre.models import (
    PreopAssessment,
    Procedure,
    StaffLeave,
    SurgicalCase,
    Theatre,
    TheatreRoster,
)

__all__ = [
    "Appointment",
    "AuditLog",
    "ClinicalHistory",
    "ClinicalReport",
    "Department",
    "DoctorSchedule",
    "Encounter",
    "EncounterCode",
    "EncounterTask",
    "HospitalClosure",
    "LabResult",
    "LabTest",
    "Patient",
    "PatientAllergy",
    "PreopAssessment",
    "Procedure",
    "ScheduleBreak",
    "ScheduleDay",
    "StaffLeave",
    "StaffMember",
    "SurgicalCase",
    "Theatre",
    "TheatreRoster",
    "User",
    "VitalSigns",
    "VoiceCall",
    "VoiceCallBooking",
]
