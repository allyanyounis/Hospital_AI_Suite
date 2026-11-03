"""Registers the Patient portal module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="portal", title="Patient portal", routers=[router])
