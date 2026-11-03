"""Staff profiles and the doctors patients can book."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.modules.auth import STAFF_ROLES, Account
from app.modules.organization import Department, get_department

from .models import StaffMember
from .schemas import StaffProfileIn


def list_staff(db: Session, department_id: int | None = None, bookable: bool | None = None) -> list[StaffMember]:
    query = select(StaffMember).join(StaffMember.account).order_by(Account.display_name)
    if department_id is not None:
        query = query.where(StaffMember.department_id == department_id)
    if bookable is not None:
        query = query.where(StaffMember.bookable.is_(bookable))
    return list(db.scalars(query))


def profile_for(db: Session, username: str) -> StaffMember | None:
    return db.scalar(select(StaffMember).where(StaffMember.username == username))


def get_bookable(db: Session, staff_id: int) -> StaffMember:
    """A doctor who takes appointments (bookable profile on an active account), or 404."""
    member = db.get(StaffMember, staff_id)
    if member is None or not member.bookable or not member.account.active:
        raise HTTPException(404, "No bookable doctor with that id")
    return member


def bookable_doctors(db: Session) -> list[StaffMember]:
    return [m for m in list_staff(db, bookable=True) if m.account.active and m.department.active]


def find_doctors(db: Session, doctor: str | None = None, department: str | None = None) -> list[StaffMember]:
    """Bookable doctors matching a spoken doctor name and/or department (name or code), for the voice agent."""
    doctors = bookable_doctors(db)

    def words(text: str) -> set[str]:
        return {w for w in text.lower().replace(".", " ").split() if w not in ("dr", "doctor")}

    if doctor and (wanted := words(doctor)):
        doctors = [m for m in doctors if wanted <= words(m.account.display_name)]
    if department:
        d = department.strip().lower()
        doctors = [m for m in doctors if d in (m.department.name.lower(), m.department.code.lower())]
    return doctors


def save_profile(db: Session, actor: str | None, username: str, req: StaffProfileIn) -> StaffMember:
    """Create or update the profile of a staff account."""
    account = db.get(Account, username)
    if account is None:
        raise HTTPException(404, "No such account")
    if account.role not in STAFF_ROLES:
        raise HTTPException(422, "Only staff accounts have a staff profile")
    department: Department = get_department(db, req.department_id)
    registration = req.registration_number or None
    if registration and db.scalar(
        select(StaffMember.id).where(StaffMember.registration_number == registration, StaffMember.username != username)
    ):
        raise HTTPException(409, "That registration number belongs to another staff member")
    member = profile_for(db, username) or StaffMember(username=username)
    member.department = department
    member.job_title = req.job_title or None
    member.specialty = req.specialty or None
    member.registration_number = registration
    member.bookable = req.bookable
    db.add(member)
    db.flush()
    audit(actor, "staff.profile_saved", db=db, user=username, department_id=department.id, bookable=req.bookable)
    return member
