"""The hospital's structure. One site for now; multi-site adds a `sites` table and `departments.site_id`."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Identity, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, now_column, one_of

DEPARTMENT_KINDS = ("clinical", "diagnostic", "support", "administrative")


class Department(Base):
    """A hospital department (Cardiology, Radiology, Pharmacy, Front Office…). Deactivated, never deleted."""

    __tablename__ = "departments"
    __table_args__ = (
        CheckConstraint(one_of("kind", DEPARTMENT_KINDS), name="kind"),
        CheckConstraint("code ~ '^[A-Z0-9_-]{2,16}$'", name="code_format"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default="clinical", server_default="clinical")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = now_column()
