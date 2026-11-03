"""Request and response bodies of the organisation API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

DepartmentKind = Literal["clinical", "diagnostic", "support", "administrative"]


class DepartmentIn(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{2,16}$")
    name: str = Field(min_length=2, max_length=120)
    kind: DepartmentKind = "clinical"

    @field_validator("code")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    kind: DepartmentKind | None = None
    active: bool | None = None


class DepartmentOut(BaseModel):
    id: int
    code: str
    name: str
    kind: DepartmentKind
    active: bool
    staff_count: int = 0
