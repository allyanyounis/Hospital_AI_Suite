"""Registers the Accounts and access module with the app (see app/core/modules.py)."""

from app.core.modules import ModuleSpec

from .router import router

MODULE = ModuleSpec(name="auth", title="Accounts and access", routers=[router])
