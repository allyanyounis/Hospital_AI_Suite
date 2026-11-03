"""Request and response bodies of the patient registry API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Sex = Literal["", "Female", "Male", "Other", "Not stated"]


class _Fields(BaseModel):
    @field_validator("date_of_birth", mode="before", check_fields=False)
    @classmethod
    def _blank_date(cls, value):
        return value or None  # forms send "" when no date is picked

    @field_validator("full_name", "mrn", "phone", "email", check_fields=False)
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class PatientIn(_Fields):
    full_name: str = Field(min_length=1, max_length=120)
    mrn: str = Field(default="", max_length=60)
    sex: Sex = ""
    date_of_birth: date | None = None
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=254)


class PatientUpdate(_Fields):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    mrn: str | None = Field(default=None, max_length=60)
    sex: Sex | None = None
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=254)


class PatientRecord(BaseModel):
    id: int
    mrn: str
    full_name: str
    sex: str
    date_of_birth: str
    phone: str
    email: str
    created_at: datetime
    has_account: bool

    @classmethod
    def of(cls, p, has_account: bool) -> "PatientRecord":
        return cls(
            id=p.id,
            mrn=p.mrn or "",
            full_name=p.full_name,
            sex=p.sex or "",
            date_of_birth=p.date_of_birth.isoformat() if p.date_of_birth else "",
            phone=p.phone or "",
            email=p.email or "",
            created_at=p.created_at,
            has_account=has_account,
        )
