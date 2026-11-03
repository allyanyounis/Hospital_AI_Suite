"""Patients module: the shared patient record and the rules for finding, updating and erasing it."""

from .models import SEXES, Patient
from .service import delete_orphan_patients, resolve_patient

__all__ = ["SEXES", "Patient", "delete_orphan_patients", "resolve_patient"]
