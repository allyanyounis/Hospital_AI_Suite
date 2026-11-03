"""Staff profiles: the hospital side of a staff account (department, title, specialty, registration, bookable)."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Identity, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column
from app.modules.auth import Account
from app.modules.organization import Department


class StaffMember(Base):
    """One per staff account. `bookable` doctors have OPD schedules and take appointments."""

    __tablename__ = "staff_members"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(ForeignKey("users.username"), unique=True)
    account: Mapped[Account] = relationship(lazy="joined")
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    department: Mapped[Department] = relationship(lazy="joined")
    job_title: Mapped[str | None] = mapped_column(String(120))
    specialty: Mapped[str | None] = mapped_column(String(120))
    registration_number: Mapped[str | None] = mapped_column(String(60), unique=True)  # medical / nursing council
    bookable: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = now_column()

    @property
    def display_name(self) -> str:
        return self.account.display_name
