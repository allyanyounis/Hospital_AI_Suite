"""Request bodies of the theatre API, and the catalogue responses. Planner responses (board, calendar, intake, case
detail) are the planner's dictionaries as they are; their TypeScript shapes are in
frontend/src/features/theatre/types.ts.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Urgency = Literal["immediate", "urgent", "expedited", "elective"]
Action = Literal[
    "earlier", "later", "book", "schedule", "unschedule", "defer", "cancel", "overrun", "surgeon", "urgency"
]


class CardiacIn(BaseModel):
    """EuroSCORE II inputs (cardiac operations)."""

    lvef: int | None = Field(default=None, ge=5, le=90)
    nyha: int | None = Field(default=None, ge=1, le=4)
    pa_systolic: int | None = Field(default=None, ge=5, le=150)
    ccs4: bool = False
    iddm: bool = False
    recent_mi: bool = False
    redo: bool = False
    lung: bool = False
    arteriopathy: bool = False
    poor_mobility: bool = False
    dialysis: bool = False
    endocarditis: bool = False
    critical: bool = False


class NewPatientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=120)
    sex: Literal["", "Female", "Male", "Other", "Not stated"] = ""
    allergies: str = Field(default="", max_length=240)


class CaseIn(BaseModel):
    """A case for an existing patient (`patient_id`) or a new one (`patient`). Without `day` it joins the waiting
    list."""

    procedure_code: str
    urgency: Urgency = "elective"
    day: date | None = None
    surgeon_id: int | None = None
    patient_id: int | None = None
    patient: NewPatientIn | None = None
    asa: int = Field(default=2, ge=1, le=6)
    weight_kg: float | None = Field(default=None, gt=0, lt=400)
    height_cm: float | None = Field(default=None, gt=30, lt=260)
    cardiac: CardiacIn | None = None

    @model_validator(mode="after")
    def _one_patient(self):
        if (self.patient_id is None) == (self.patient is None):
            raise ValueError("Give either patient_id or patient")
        return self

    def planner(self) -> dict:
        return self.model_dump(exclude_none=True) | {"cardiac": self.cardiac.model_dump() if self.cardiac else None}


class MoveIn(BaseModel):
    case: int
    date: date
    surgeon_id: int | None = None


class IntakeIn(BaseModel):
    """Place a waiting case (`case_id`) or a new emergency (the CaseIn fields) by urgency."""

    case_id: int | None = None
    urgency: Urgency | None = None
    procedure_code: str | None = None
    patient_id: int | None = None
    patient: NewPatientIn | None = None
    surgeon_id: int | None = None
    asa: int = Field(default=2, ge=1, le=6)
    weight_kg: float | None = None
    height_cm: float | None = None
    cardiac: CardiacIn | None = None
    moves: list[MoveIn] = []  # confirm only: the suggested moves the user ticked

    def planner(self) -> dict:
        out = self.model_dump(exclude_none=True, exclude={"moves", "cardiac"})
        out["cardiac"] = self.cardiac.model_dump() if self.cardiac else None
        out["moves"] = [m.model_dump() for m in self.moves]
        return out


class ActionIn(BaseModel):
    day: date | None = None  # schedule, defer
    surgeon_id: int | None = None  # schedule, defer, surgeon
    minutes: int = Field(default=15, ge=5, le=240)  # overrun
    urgency: Urgency | None = None  # urgency


class RosterDay(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start: int = Field(ge=0, le=24 * 60)  # minutes after midnight
    end: int = Field(ge=0, le=24 * 60)

    @model_validator(mode="after")
    def _order(self):
        if self.end <= self.start:
            raise ValueError("The end must be after the start")
        return self


class RosterIn(BaseModel):
    days: list[RosterDay]

    @model_validator(mode="after")
    def _unique(self):
        if len({d.weekday for d in self.days}) != len(self.days):
            raise ValueError("One entry per weekday")
        return self


class LeaveIn(BaseModel):
    staff_id: int
    starts_on: date
    ends_on: date
    reason: str = Field(default="Leave", max_length=120)

    @model_validator(mode="after")
    def _order(self):
        if self.ends_on < self.starts_on:
            raise ValueError("Pick a start and an end date")
        return self


class TheatreOut(BaseModel):
    id: int
    code: str
    name: str
    specialty: str
    cleaning_minutes: int

    @classmethod
    def of(cls, t) -> "TheatreOut":
        return cls(id=t.id, code=t.code, name=t.name, specialty=t.specialty, cleaning_minutes=t.cleaning_minutes)


class ProcedureOut(BaseModel):
    code: str
    title: str
    specialty: str
    minutes: int
    risk_model: str

    @classmethod
    def of(cls, p) -> "ProcedureOut":
        return cls(code=p.code, title=p.title, specialty=p.specialty, minutes=p.minutes, risk_model=p.risk_model)


class ExperimentIn(BaseModel):
    seed: int = 20261101
    disruption: Literal["", "overrun", "emergency", "room_outage", "pacu"] = ""
    second: bool = False  # add an emergency on top of the disruption
    when: Literal["early", "midday", "late"] = "midday"
    profile: Literal["balanced", "protect_electives", "avoid_overtime"] = "balanced"
    stress: bool = False
