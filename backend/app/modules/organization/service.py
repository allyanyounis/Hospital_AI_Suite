"""Departments: create, rename, (de)activate. Every change is audited."""

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.audit import audit

from .models import Department
from .schemas import DepartmentIn, DepartmentUpdate


def list_departments(db: Session) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.name)))


def get_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(404, "No such department")
    return department


def create_department(db: Session, actor: str | None, req: DepartmentIn) -> Department:
    clash = db.scalar(select(Department.id).where(or_(Department.code == req.code, Department.name == req.name)))
    if clash:
        raise HTTPException(409, "A department with that code or name already exists")
    department = Department(code=req.code, name=req.name, kind=req.kind)
    db.add(department)
    db.flush()
    audit(actor, "department.created", db=db, department_id=department.id, code=req.code)
    return department


def update_department(db: Session, actor: str | None, department: Department, req: DepartmentUpdate) -> Department:
    if req.name is not None and req.name.strip() != department.name:
        if db.scalar(select(Department.id).where(Department.name == req.name.strip())):
            raise HTTPException(409, "A department with that name already exists")
        department.name = req.name.strip()
    if req.kind is not None:
        department.kind = req.kind
    if req.active is not None:
        department.active = req.active
    audit(actor, "department.updated", db=db, department_id=department.id, active=department.active)
    return department
