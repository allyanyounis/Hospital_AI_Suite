"""Request and response bodies of the appointments API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PractitionerRef(BaseModel):
    id: int
    display_name: str
    department: str


class AppointmentOut(BaseModel):
    """Extra fields contributed by other modules (see extensions.py), e.g. `transcript`, are passed through."""

    model_config = ConfigDict(extra="allow")

    id: int
    patient_id: int
    patient_name: str
    reason: str | None
    start_time: datetime
    canceled: bool
    created_at: datetime
    booked_via: str
    practitioner: PractitionerRef

    @classmethod
    def of(cls, a, extra: dict | None = None) -> "AppointmentOut":
        doctor = a.practitioner
        return cls(
            id=a.id,
            patient_id=a.patient_id,
            patient_name=a.patient.full_name,
            reason=a.reason,
            start_time=a.start_time,
            canceled=a.canceled,
            created_at=a.created_at,
            booked_via=a.booked_via,
            practitioner=PractitionerRef(
                id=doctor.id, display_name=doctor.account.display_name, department=doctor.department.name
            ),
            **(extra or {}),
        )


class BookingRequest(BaseModel):
    """A front-desk booking. start_time is hospital-local, e.g. "2026-11-04T10:30"."""

    patient_id: int
    practitioner_id: int
    start_time: datetime
    reason: str = Field(default="", max_length=255)


class Availability(BaseModel):
    date: date
    slots: list[str]
