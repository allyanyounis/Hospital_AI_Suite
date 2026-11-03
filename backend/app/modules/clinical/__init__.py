"""Clinical data module: a patient's lab results, vital signs, reports, history and allergies, shared by the patient
chart, the theatre list and (later) the scribe."""

from .models import (
    REPORT_KINDS,
    ClinicalHistory,
    ClinicalReport,
    LabResult,
    LabTest,
    PatientAllergy,
    VitalSigns,
)
from .service import (
    add_allergy,
    add_history,
    add_report,
    allergy_text,
    ensure_lab_tests,
    latest_lab_values,
    record_lab,
    record_vitals,
)

__all__ = [
    "REPORT_KINDS",
    "ClinicalHistory",
    "ClinicalReport",
    "LabResult",
    "LabTest",
    "PatientAllergy",
    "VitalSigns",
    "add_allergy",
    "add_history",
    "add_report",
    "allergy_text",
    "ensure_lab_tests",
    "latest_lab_values",
    "record_lab",
    "record_vitals",
]
