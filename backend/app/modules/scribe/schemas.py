"""Request and response bodies of the scribe API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .notes import GeneratedNote
from .transcription import Transcript


class EncounterOut(BaseModel):
    id: str
    transcript: Transcript


class SampleRequest(BaseModel):
    sample_id: str


class NoteRequest(BaseModel):
    template_id: str
    clinician_speaker: int = 0


class NoteBody(BaseModel):
    note: GeneratedNote


class DocumentRequest(BaseModel):
    type_id: str


class PatientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mrn: str = Field(default="", max_length=60)
    sex: Literal["", "Female", "Male", "Other", "Not stated"] = ""
    dob: date | None = None
    visit_type: str = Field(default="", max_length=60)

    @field_validator("name", "mrn", "visit_type")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("dob", mode="before")
    @classmethod
    def _blank_dob(cls, value):
        return value or None  # the form sends "" when no date is picked
