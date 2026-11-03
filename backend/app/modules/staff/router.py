"""Staff directory (anyone on staff) and staff profiles (staff.manage)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth import User, require

from . import service
from .schemas import StaffOut, StaffProfileIn

router = APIRouter(prefix="/api/staff", tags=["staff"])


@router.get("", response_model=list[StaffOut])
def list_staff(
    department_id: int | None = None,
    bookable: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require("staff.view")),
):
    return [StaffOut.of(m) for m in service.list_staff(db, department_id, bookable)]


@router.put("/{username}", response_model=StaffOut)
def save_profile(
    username: str, req: StaffProfileIn, db: Session = Depends(get_db), user: User = Depends(require("staff.manage"))
):
    member = service.save_profile(db, user.username, username, req)
    db.commit()
    return StaffOut.of(member)
