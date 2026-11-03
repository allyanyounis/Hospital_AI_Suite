"""AI voice receptionist: a booking channel. VAPI webhooks book, check and cancel appointments through the
appointments module; this module keeps the calls, their transcripts and which bookings each call made."""

from .models import VoiceCall, VoiceCallBooking

__all__ = ["VoiceCall", "VoiceCallBooking"]
