"""Request and response bodies of the staff API."""

from pydantic import BaseModel, Field, field_validator


class StaffProfileIn(BaseModel):
    department_id: int
    job_title: str = Field(default="", max_length=120)
    specialty: str = Field(default="", max_length=120)
    registration_number: str = Field(default="", max_length=60)
    bookable: bool = False

    @field_validator("job_title", "specialty", "registration_number")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class DepartmentRef(BaseModel):
    id: int
    code: str
    name: str


class StaffOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    active: bool
    department: DepartmentRef
    job_title: str
    specialty: str
    registration_number: str
    bookable: bool

    @classmethod
    def of(cls, m) -> "StaffOut":
        return cls(
            id=m.id,
            username=m.username,
            display_name=m.account.display_name,
            role=m.account.role,
            active=m.account.active,
            department=DepartmentRef(id=m.department.id, code=m.department.code, name=m.department.name),
            job_title=m.job_title or "",
            specialty=m.specialty or "",
            registration_number=m.registration_number or "",
            bookable=m.bookable,
        )
