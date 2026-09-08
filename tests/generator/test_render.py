from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from stonepy._generator import render


def test_ruff_subprocesses_use_absolute_project_config(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", run)
    render.format_python("value = 1\n")
    assert [argv[1] for argv in commands] == ["format", "check", "format"]
    assert render.RUFF_CONFIG_PATH.is_absolute()
    for argv in commands:
        assert argv[argv.index("--config") + 1] == str(render.RUFF_CONFIG_PATH)


def test_rendering_ignores_ambient_ruff_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    monkeypatch.chdir(tmp_path)
    source = 'result = function("' + "x" * 78 + '")\n'
    assert len(source.rstrip()) == 99
    assert render.format_python(source) == source


def test_rendering_requires_project_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "absent.toml"
    monkeypatch.setattr(render, "RUFF_CONFIG_PATH", missing)
    with pytest.raises(RuntimeError, match=f"ruff config not found: {missing}"):
        render.format_python("value = 1\n")
