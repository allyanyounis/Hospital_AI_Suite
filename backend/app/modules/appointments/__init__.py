"""Appointments module: OPD booking rules and the appointment record, used by every booking channel (voice
receptionist, front desk, patient portal). Channels attach their own details through `register_detail_provider`."""

from . import booking
from .extensions import details_for, register_detail_provider
from .models import BOOKING_CHANNELS, Appointment

__all__ = ["BOOKING_CHANNELS", "Appointment", "booking", "details_for", "register_detail_provider"]
