"""Registers the AI voice receptionist with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec
from app.modules.appointments import register_detail_provider

from . import calls, vapi


def _setup() -> None:
    register_detail_provider(calls.transcripts_for)  # appointment listings show each voice booking's transcript


MODULE = ModuleSpec(name="reception", title="AI voice receptionist", routers=[vapi.router], setup=_setup)
