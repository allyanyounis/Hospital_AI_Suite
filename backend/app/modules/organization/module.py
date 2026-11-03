"""Registers the Organisation module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="organization", title="Organisation", routers=[router])
