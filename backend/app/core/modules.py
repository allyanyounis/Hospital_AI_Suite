"""The module registry. Every feature package declares itself in `app/modules/<name>/module.py`:

    MODULE = ModuleSpec(name="laboratory", title="Laboratory", routers=[router])

and `app/main.py` mounts the packages listed in INSTALLED_MODULES. A module that extends another (e.g. adds
fields to appointment listings) does so in `setup`, which runs once when the app is built.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module

from fastapi import APIRouter


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    title: str
    routers: list[APIRouter] = field(default_factory=list)
    setup: Callable[[], None] | None = None


def load_modules(names: list[str]) -> list[ModuleSpec]:
    """Import each module's `module.py` and run its setup hook, in the order given."""
    specs = []
    for name in names:
        spec: ModuleSpec = import_module(f"app.modules.{name}.module").MODULE
        if spec.name != name:
            raise RuntimeError(f"app/modules/{name}/module.py declares name {spec.name!r}")
        if spec.setup:
            spec.setup()
        specs.append(spec)
    return specs
