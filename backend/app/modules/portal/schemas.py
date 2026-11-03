"""Response bodies of the patient portal API. Only the patient's own data, never staff or clinical notes."""

from datetime import datetime

from pydantic import BaseModel


class PortalProfile(BaseModel):
    name: str
    mrn: str
    dob: str
    sex: str


class PortalAppointment(BaseModel):
    id: int
    reason: str | None
    start_time: datetime
    canceled: bool
    created_at: datetime
    doctor: str
    department: str

    @classmethod
    def of(cls, a) -> "PortalAppointment":
        return cls(
            id=a.id,
            reason=a.reason,
            start_time=a.start_time,
            canceled=a.canceled,
            created_at=a.created_at,
            doctor=a.practitioner.account.display_name,
            department=a.practitioner.department.name,
        )
