from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.typing.consumer_model_constructors import model_constructors
from tests.typing.from_env_overrides import valid_overrides

ROOT = Path(__file__).resolve().parents[1]
_REQUIRES_MYPY = pytest.mark.skipif(
    importlib.util.find_spec("mypy") is None or shutil.which("uv") is None,
    reason="consumer static checks need dev tools (excluded from runtime-only installs)",
)


def _mypy(path: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "uv",
            "run",
            "--offline",
            "--no-sync",
            "mypy",
            "--config-file",
            str(ROOT / "pyproject.toml"),
            "--cache-dir",
            str(tmp_path / "mypy-cache"),
            "--no-incremental",
            str(path),
        ],
        cwd=ROOT,
        env={**os.environ, "UV_CACHE_DIR": "/tmp/stonepy-uv-cache"},
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _without_ignores(fixture: Path, tmp_path: Path) -> Path:
    path = tmp_path / fixture.name
    path.write_text(re.sub(r"  # type: ignore\[[^]]+\]", "", fixture.read_text()))
    return path


@_REQUIRES_MYPY
def test_from_env_static_overrides_are_checked(tmp_path: Path) -> None:
    fixture = ROOT / "tests/typing/from_env_overrides.py"
    accepted = _mypy(fixture, tmp_path)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    diagnosed = _mypy(_without_ignores(fixture, tmp_path), tmp_path)
    assert diagnosed.returncode == 1, diagnosed.stdout + diagnosed.stderr
    assert 'Unexpected keyword argument "typo"' in diagnosed.stdout
    assert 'Argument "max_retries"' in diagnosed.stdout
    assert diagnosed.stdout.count(": error:") == 2
    assert "[call-arg]" in diagnosed.stdout
    assert "[arg-type]" in diagnosed.stdout


@_REQUIRES_MYPY
def test_consumer_model_constructor_typing(tmp_path: Path) -> None:
    fixture = ROOT / "tests/typing/consumer_model_constructors.py"
    accepted = _mypy(fixture, tmp_path)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    diagnosed = _mypy(_without_ignores(fixture, tmp_path), tmp_path)
    assert diagnosed.returncode == 1, diagnosed.stdout + diagnosed.stderr
    errors = [line for line in diagnosed.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 7, diagnosed.stdout
    assert all("Unexpected keyword argument" in line and "[call-arg]" in line for line in errors)
    for model in ("ApiLogOnRequestDTO", "IdentifierDTO", "RequestIdentifierDTO"):
        assert f'for "{model}"' in diagnosed.stdout


def test_consumer_examples_accept_valid_runtime_forms() -> None:
    config = valid_overrides()
    assert config.read_timeout == 60.0
    assert config.status_decoder is None
    models = model_constructors()
    for alias, python in zip(models[::2], models[1::2], strict=True):
        assert alias.model_dump() == python.model_dump()


def test_pyright_job_is_advisory() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "  pyright:\n" in workflow and "  ci:\n" in workflow, (
        "ci.yml must declare both the pyright job and the ci aggregate"
    )
    assert workflow.index("  pyright:\n") < workflow.index("  ci:\n"), (
        "This text-based assertion requires pyright to be declared before ci; "
        "update the job extraction below if the workflow jobs are reordered"
    )
    job, aggregate = workflow.split("  pyright:\n", 1)[1].split("  ci:\n", 1)
    assert "    continue-on-error: true\n" in job
    assert "uv python install 3.12" in job
    assert "uv sync --locked --extra dev --python 3.12" in job
    assert "uv run --locked pyright tests" in job
    assert "pyright" not in aggregate
