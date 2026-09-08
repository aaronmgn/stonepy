from __future__ import annotations

import importlib.util
import json
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
_REQUIRES_PYRIGHT = pytest.mark.skipif(
    importlib.util.find_spec("pyright") is None or shutil.which("uv") is None,
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
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _without_ignores(fixture: Path, tmp_path: Path) -> Path:
    path = tmp_path / fixture.name
    path.write_text(re.sub(r"  # type: ignore\[[^]]+\]", "", fixture.read_text()))
    return path


def _pyright(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--offline", "--no-sync", "pyright", "--outputjson", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


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


@pytest.mark.parametrize(
    "checker",
    [
        pytest.param("mypy", marks=_REQUIRES_MYPY),
        pytest.param("pyright", marks=[_REQUIRES_PYRIGHT, pytest.mark.pyright]),
    ],
)
def test_consumer_model_constructor_typing(checker: str, tmp_path: Path) -> None:
    fixture = ROOT / "tests/typing/consumer_model_constructors.py"
    accepted = _mypy(fixture, tmp_path) if checker == "mypy" else _pyright(fixture)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    calls = []
    for names in (
        ("UserName", "Password", "AppKey", "AppVersion", "AppComments"),
        ("user_name", "password", "app_key", "app_version", "app_comments"),
    ):
        valid = "ApiLogOnRequestDTO(" + ", ".join(f'{name}="x"' for name in names) + ")"
        calls.extend(
            [
                valid.replace(f'{names[0]}="x"', f"{names[0]}=123"),  # wrong field type
                valid[:-1] + ', typo="x")',  # unknown keyword
                valid.replace(f'{names[0]}="x", ', ""),  # missing required field
                valid.replace(names[0], "user_name" if names[0] == "UserName" else "UserName"),
                # Mixing spellings is valid at runtime but outside either overload.
            ]
        )
    invalid = tmp_path / "invalid_constructors.py"
    invalid.write_text("from stonepy.models import ApiLogOnRequestDTO\n" + "\n".join(calls) + "\n")
    diagnosed = _mypy(invalid, tmp_path) if checker == "mypy" else _pyright(invalid)
    assert diagnosed.returncode == 1, diagnosed.stdout + diagnosed.stderr
    if checker == "mypy":
        error_lines = {
            int(line)
            for line in re.findall(r"invalid_constructors\.py:(\d+): error:", diagnosed.stdout)
        }
    else:
        error_lines = {
            diagnostic["range"]["start"]["line"] + 1
            for diagnostic in json.loads(diagnosed.stdout)["generalDiagnostics"]
            if diagnostic["severity"] == "error" and diagnostic["file"] == str(invalid)
        }
    assert error_lines == set(range(2, len(calls) + 2)), diagnosed.stdout


def test_consumer_examples_accept_valid_runtime_forms() -> None:
    config = valid_overrides()
    assert config.read_timeout == 60.0
    assert config.status_decoder is None
    models = model_constructors()
    for alias, python in zip(models[::2], models[1::2], strict=True):
        assert alias.model_dump() == python.model_dump()


def test_pyright_job_gates_ci() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "  pyright:\n" in workflow and "  ci:\n" in workflow, (
        "ci.yml must declare both the pyright job and the ci aggregate"
    )
    assert workflow.index("  pyright:\n") < workflow.index("  ci:\n"), (
        "This text-based assertion requires pyright to be declared before ci; "
        "update the job extraction below if the workflow jobs are reordered"
    )
    job, aggregate = workflow.split("  pyright:\n", 1)[1].split("  ci:\n", 1)
    assert "continue-on-error" not in job
    assert "uv python install 3.12" in job
    assert "uv sync --locked --extra dev --python 3.12" in job
    assert "uv run --locked python -m mypy.stubtest stonepy.models" in job
    assert "uv run --locked pyright tests src/stonepy/models" in job
    assert "-m pyright tests/test_consumer_typing.py" in job
    assert 'uv run --locked pytest --cov -m "not pyright"' in workflow
    needs = re.search(r"^    needs: \[([^]]+)\]$", aggregate, re.MULTILINE)
    assert needs is not None
    assert "pyright" in {name.strip() for name in needs.group(1).split(",")}
    assert 'test "${{ needs.pyright.result }}" = success' in aggregate
