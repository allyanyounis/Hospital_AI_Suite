"""Module boundaries (see backend/README.md): core imports no feature module, and modules use each other only
through their public package (app.modules.<name>), never another module's internal files."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"
COMPOSITION_ROOTS = {"main.py", "models.py", "__main__.py"}  # wire every module together by design


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0]


def _files(folder: str) -> list[Path]:
    return sorted((APP / folder).rglob("*.py"))


@pytest.mark.parametrize("path", _files("core"), ids=lambda p: p.name)
def test_core_does_not_import_modules(path):
    assert not [m for m in _imports(path) if m.startswith("app.modules")]


@pytest.mark.parametrize("path", _files("modules"), ids=lambda p: str(p.relative_to(APP / "modules")))
def test_modules_use_each_other_only_through_public_packages(path):
    own = path.relative_to(APP / "modules").parts[0]
    deep = [
        m for m in _imports(path) if m.startswith("app.modules.") and m.split(".")[2] != own and len(m.split(".")) > 3
    ]
    assert not deep, f"import the public package instead: {deep}"


def test_composition_roots_are_the_only_top_level_files():
    assert {p.name for p in APP.glob("*.py")} - {"__init__.py"} == COMPOSITION_ROOTS


def test_every_module_is_registered_and_installed():
    from app.main import INSTALLED_MODULES

    packages = sorted(p.name for p in (APP / "modules").iterdir() if (p / "__init__.py").exists())
    assert sorted(INSTALLED_MODULES) == packages, "list every module in INSTALLED_MODULES (app/main.py)"
    assert all((APP / "modules" / name / "module.py").exists() for name in packages)
