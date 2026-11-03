"""Staff module: staff profiles (department, title, specialty, registration) and which doctors take bookings."""

from .models import StaffMember
from .service import bookable_doctors, find_doctors, get_bookable, profile_for, save_profile

__all__ = ["StaffMember", "bookable_doctors", "find_doctors", "get_bookable", "profile_for", "save_profile"]
