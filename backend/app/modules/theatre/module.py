"""Registers the Operating theatres module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="theatre", title="Operating theatres", routers=[router])
