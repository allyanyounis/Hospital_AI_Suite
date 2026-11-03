"""Registers the Staff module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="staff", title="Staff", routers=[router])
