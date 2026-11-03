"""Organisation module: the hospital's departments (and, later, sites, wards and other locations)."""

from .models import DEPARTMENT_KINDS, Department
from .service import get_department

__all__ = ["DEPARTMENT_KINDS", "Department", "get_department"]
