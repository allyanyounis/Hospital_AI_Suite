"""Registers the AI medical scribe module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from . import live_router, router

MODULE = ModuleSpec(name="scribe", title="AI medical scribe", routers=[router.router, live_router.router])
