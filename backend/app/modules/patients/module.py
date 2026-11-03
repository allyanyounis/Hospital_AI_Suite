"""Registers the Patient registry module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="patients", title="Patient registry", routers=[router])
