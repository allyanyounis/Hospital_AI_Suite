"""Request and response bodies of the auth API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .permissions import Role

USERNAME = r"^[a-zA-Z0-9._-]{3,64}$"


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    password: str


class NewPatient(BaseModel):
    """Details for the patient record a patient account is linked to (matched by MRN when given)."""

    mrn: str = Field(default="", max_length=60)
    dob: date | None = None
    sex: Literal["", "Female", "Male", "Other", "Not stated"] = ""

    @field_validator("dob", mode="before")
    @classmethod
    def _blank_dob(cls, value):
        return value or None


class AccountCreate(BaseModel):
    username: str = Field(pattern=USERNAME)
    display_name: str = Field(min_length=1, max_length=120)
    role: Role
    password: str
    patient: NewPatient | None = None


class AccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    active: bool | None = None


class LinkedPatient(BaseModel):
    id: int
    name: str
    mrn: str


class AccountOut(BaseModel):
    username: str
    display_name: str
    role: Role
    active: bool
    created_at: datetime
    patient: LinkedPatient | None

    @classmethod
    def of(cls, account) -> "AccountOut":
        p = account.patient
        return cls(
            username=account.username,
            display_name=account.display_name,
            role=account.role,
            active=account.active,
            created_at=account.created_at,
            patient=LinkedPatient(id=p.id, name=p.full_name, mrn=p.mrn or "") if p else None,
        )
