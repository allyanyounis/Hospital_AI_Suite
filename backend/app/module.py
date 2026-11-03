"""What a feature module plugs into the app. Each module exposes one `module = Module(...)` in <module>/module.py."""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from fastapi import APIRouter


@dataclass(frozen=True)
class Module:
    name: str
    # Included in this order
    routers: Sequence[APIRouter] = ()
    # Run once when the backend starts, after the database is ready
    on_startup: Sequence[Callable[[], None]] = ()
    # Adds non-secret keys to GET /api/config (read by the UI before sign-in)
    public_config: Callable[[], Awaitable[dict]] | None = None
