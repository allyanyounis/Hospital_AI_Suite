"""Registers the OPD scheduling module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="scheduling", title="OPD scheduling", routers=[router])
