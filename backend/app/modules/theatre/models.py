"""Operating theatres: the rooms, the operations they do, the surgical cases on their lists, each case's pre-op
assessment, and the surgeons' theatre sessions and leave.

A surgeon is a staff member whose specialty matches a theatre's (e.g. "Trauma"); their theatre sessions are kept
apart from their OPD schedule. A case with no `scheduled_on` is on the waiting list.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column, one_of

URGENCIES = ("immediate", "urgent", "expedited", "elective")  # NCEPOD classification
RISK_MODELS = ("vitaldb", "euroscore2")


class Theatre(Base):
    __tablename__ = "theatres"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)  # "OR 1"
    name: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    specialty: Mapped[str] = mapped_column(String(60))
    cleaning_minutes: Mapped[int] = mapped_column(SmallInteger)  # turnover between two cases
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Procedure(Base):
    """An operation and its planned minutes per phase. `variance` (min²) is the spread of the whole case length."""

    __tablename__ = "procedures"
    __table_args__ = (CheckConstraint(one_of("risk_model", RISK_MODELS), name="risk_model"),)

    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # OPS code
    title: Mapped[str] = mapped_column(String(160))
    specialty: Mapped[str] = mapped_column(String(60))
    induction: Mapped[int] = mapped_column(SmallInteger)
    lead_in: Mapped[int] = mapped_column(SmallInteger)
    incision: Mapped[int] = mapped_column(SmallInteger)
    lead_out: Mapped[int] = mapped_column(SmallInteger)
    emergence: Mapped[int] = mapped_column(SmallInteger)
    variance: Mapped[float] = mapped_column(Float)
    risk_model: Mapped[str] = mapped_column(String(12), default="vitaldb", server_default="vitaldb")
    euro_weight: Mapped[int | None] = mapped_column(SmallInteger)  # EuroSCORE II weight of the intervention
    aorta: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    source: Mapped[str] = mapped_column(Text, default="", server_default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    @property
    def minutes(self) -> int:
        return self.induction + self.lead_in + self.incision + self.lead_out + self.emergence


class SurgicalCase(Base):
    """One operation for one patient. Ordered within a theatre's day by `seq`; `deferred` marks a case moved off its
    original day. Canceled cases are kept for the record."""

    __tablename__ = "surgical_cases"
    __table_args__ = (
        CheckConstraint(one_of("urgency", URGENCIES), name="urgency"),
        CheckConstraint("overrun_minutes >= 0", name="overrun_minutes"),
        Index("ix_surgical_cases_scheduled_on_theatre_id", "scheduled_on", "theatre_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    procedure_code: Mapped[str] = mapped_column(ForeignKey("procedures.code"))
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id"))
    scheduled_on: Mapped[date | None] = mapped_column(Date)
    seq: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    urgency: Mapped[str] = mapped_column(String(10), default="elective", server_default="elective")
    surgeon_id: Mapped[int | None] = mapped_column(ForeignKey("staff_members.id"), index=True)
    overrun_minutes: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    deferred: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    canceled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.username"))
    created_at: Mapped[datetime] = now_column()
    updated_at: Mapped[datetime] = now_column(onupdate=func.now())
    preop: Mapped["PreopAssessment | None"] = relationship(
        lazy="joined", cascade="all, delete-orphan", passive_deletes=True
    )


class PreopAssessment(Base):
    """The anaesthetic assessment of a case. The EuroSCORE II inputs (lvef onwards) are recorded for cardiac cases."""

    __tablename__ = "preop_assessments"
    __table_args__ = (
        CheckConstraint("asa BETWEEN 1 AND 6", name="asa"),
        CheckConstraint("lvef BETWEEN 5 AND 90", name="lvef"),
        CheckConstraint("nyha BETWEEN 1 AND 4", name="nyha"),
    )

    case_id: Mapped[int] = mapped_column(ForeignKey("surgical_cases.id", ondelete="CASCADE"), primary_key=True)
    asa: Mapped[int] = mapped_column(SmallInteger)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    lvef: Mapped[int | None] = mapped_column(SmallInteger)  # %
    nyha: Mapped[int | None] = mapped_column(SmallInteger)
    pa_systolic: Mapped[int | None] = mapped_column(SmallInteger)  # mmHg
    ccs4: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    iddm: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    recent_mi: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    redo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    lung: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    arteriopathy: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    poor_mobility: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    dialysis: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    endocarditis: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    critical: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class TheatreRoster(Base):
    """A surgeon's operating hours on one weekday (0 = Monday). No row: they do not operate that day."""

    __tablename__ = "theatre_rosters"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday"),
        CheckConstraint("ends > starts", name="ends_after_starts"),
    )

    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id", ondelete="CASCADE"), primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    starts: Mapped[time] = mapped_column(Time)
    ends: Mapped[time] = mapped_column(Time)


class StaffLeave(Base):
    __tablename__ = "staff_leave"
    __table_args__ = (CheckConstraint("ends_on >= starts_on", name="ends_after_starts"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id", ondelete="CASCADE"), index=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(120), default="Leave", server_default="Leave")
    created_at: Mapped[datetime] = now_column()
