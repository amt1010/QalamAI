"""Architectural fitness functions.

The modular monolith is only modular while the boundaries hold. Reviewer
vigilance does not survive four years and a dozen contributors; these tests do.
Running import-linter from pytest means a boundary violation fails the same
command a developer already runs, not only CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_layering_contracts_hold() -> None:
    """No module imports upward through the layer stack.

    Contracts are declared under ``[tool.importlinter]`` in pyproject.toml.
    """
    result = subprocess.run(
        [sys.executable, "-m", "importlinter.cli", "lint"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Architectural boundary violation:\n{result.stdout}\n{result.stderr}"
    )


def test_application_layer_cannot_import_a_concrete_adapter() -> None:
    """The rule that makes 'replaceable AI components' real.

    An orchestrator that reaches for a concrete engine has silently welded the
    platform to one model. ``application`` sits below ``adapters`` in the layer
    stack precisely so this is a build failure.
    """
    application = REPO_ROOT / "backend" / "src" / "qalam" / "application"
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in application.rglob("*.py")
        if "qalam.adapters" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Application layer references adapters directly: {offenders}"


def test_domain_does_not_import_a_web_framework() -> None:
    """Keeps the domain usable from training scripts and batch jobs."""
    domain = REPO_ROOT / "backend" / "src" / "qalam" / "domain"
    forbidden = ("fastapi", "starlette", "uvicorn", "pydantic")
    offenders: list[tuple[str, str]] = []
    for path in domain.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        offenders.extend(
            (str(path.relative_to(REPO_ROOT)), name)
            for name in forbidden
            if f"import {name}" in text
        )
    assert not offenders, f"Domain layer imports framework code: {offenders}"
