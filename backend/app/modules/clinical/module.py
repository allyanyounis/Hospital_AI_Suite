"""Registers the Clinical data module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="clinical", title="Clinical data", routers=[router])
