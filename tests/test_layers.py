"""The layering rules, enforced by import-linter.

``REFACTOR.md`` states three rules.  Two of them are import contracts and live in
``[tool.importlinter]`` in ``pyproject.toml``; this module runs them and checks
that every one of them is actually evaluated.  The third rule - nothing below
``display`` draws - is not an import property, so it is proved at runtime in
``tests/test_api.py`` instead.
"""

import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

CONTRACTS = (
    "errors is a leaf",
    "pattern is a leaf",
    "the solver does not draw",
    "measurement does not solve or draw",
    "the renderer does not solve",
)


def lint_imports_executable() -> str:
    """The ``lint-imports`` entry point that belongs to the running interpreter."""
    found = shutil.which("lint-imports")
    if found:
        return found
    scripts = pathlib.Path(sys.executable).parent
    for candidate in sorted(scripts.glob("lint-imports*")):
        return str(candidate)
    raise AssertionError(
        "import-linter is not installed; it is part of the dev extra: uv sync --extra dev"
    )


@pytest.fixture(scope="module")
def lint_output() -> str:
    done = subprocess.run(
        [lint_imports_executable(), "--no-cache", "--no-logo"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, f"stdout:\n{done.stdout}\nstderr:\n{done.stderr}"
    return done.stdout


def test_layering_contracts_all_pass(lint_output):
    assert f"Contracts: {len(CONTRACTS)} kept, 0 broken." in lint_output


def test_every_contract_is_evaluated(lint_output):
    """Guards against a silently empty config making the check above vacuous."""
    for name in CONTRACTS:
        assert f"{name} KEPT" in lint_output, f"{name} was not evaluated"


def test_the_contract_list_matches_the_configuration():
    config = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for name in CONTRACTS:
        assert f'name = "{name}"' in config, f"{name} is missing from pyproject.toml"
