"""Accounts: staff (admin, doctor) and patients. A patient account is linked to exactly one patient record."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, now_column, one_of
from app.modules.patients import Patient

from .permissions import ROLES


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(one_of("role", ROLES), name="role"),
        CheckConstraint("(role = 'patient') = (patient_id IS NOT NULL)", name="patient_link"),
    )

    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="doctor", server_default="doctor")
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = now_column()
    # Patient accounts only: whose record this is (one account per patient)
    patient_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("patients.id"), unique=True)
    patient: Mapped[Patient | None] = relationship(lazy="joined")
    # Part of every session token; bumping it (password reset, role change, disable) signs the user out everywhere
    session_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
