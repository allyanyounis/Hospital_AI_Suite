"""Departments API. Anyone on staff may read the list; changing it needs organization.manage."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.modules.auth import User, require

from . import service
from .models import Department
from .schemas import DepartmentIn, DepartmentOut, DepartmentUpdate

router = APIRouter(prefix="/api/departments", tags=["organization"])
manage = require("organization.manage")


def _staff_counts(db: Session) -> dict[int, int]:
    """Staff per department. Read through the table metadata so this module does not import the staff module
    (staff depends on organisation, not the other way round)."""
    staff = Base.metadata.tables.get("staff_members")
    if staff is None:
        return {}
    return dict(db.execute(select(staff.c.department_id, func.count()).group_by(staff.c.department_id)).all())


def _out(department: Department, counts: dict[int, int]) -> DepartmentOut:
    return DepartmentOut(
        id=department.id,
        code=department.code,
        name=department.name,
        kind=department.kind,
        active=department.active,
        staff_count=counts.get(department.id, 0),
    )


@router.get("", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(require("staff.view"))):
    counts = _staff_counts(db)
    return [_out(d, counts) for d in service.list_departments(db)]


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(req: DepartmentIn, db: Session = Depends(get_db), user: User = Depends(manage)):
    department = service.create_department(db, user.username, req)
    db.commit()
    return _out(department, {})


@router.patch("/{department_id}", response_model=DepartmentOut)
def update_department(
    department_id: int, req: DepartmentUpdate, db: Session = Depends(get_db), user: User = Depends(manage)
):
    department = service.update_department(db, user.username, service.get_department(db, department_id), req)
    db.commit()
    return _out(department, _staff_counts(db))
