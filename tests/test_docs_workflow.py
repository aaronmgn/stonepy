from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Simulate read-only git queries so the real classifier can run without creating commits or tags.
_GIT = r"""
git() {
  case "$1" in
    rev-parse)
      test "$4" = 'refs/tags/v0.4.1^{commit}' || return 1
      printf '%s\n' tag-commit
      ;;
    cat-file)
      test "$3" != 'before:src/stonepy/_version.py' && test "$LEGACY_TAG" != 1
      ;;
    show)
      case "$2" in
        before:src/stonepy/__init__.py)
          printf '__version__ = "0.4.1"\n'
          ;;
        current:src/stonepy/_version.py)
          printf '__version__ = "%s"\n' "$CURRENT_VERSION"
          ;;
        tag-commit:src/stonepy/_version.py|tag-commit:src/stonepy/__init__.py)
          printf '__version__ = "%s"\n' "$TAG_VERSION"
          ;;
        *) return 1 ;;
      esac
      ;;
    *) return 1 ;;
  esac
}
"""


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, {"mode": "dev", "version": "", "source_sha": "current"}),
        (
            {"INPUT_VERSION": "0.4.1"},
            {"mode": "release", "version": "0.4.1", "source_sha": "tag-commit"},
        ),
        (
            {"INPUT_VERSION": "0.4.1", "LEGACY_TAG": "1"},
            {"mode": "release", "version": "0.4.1", "source_sha": "tag-commit"},
        ),
        ({"INPUT_VERSION": "0.5.0"}, None),
        ({"INPUT_VERSION": "0.4.1", "TAG_VERSION": "0.4.2"}, None),
        (
            {"EVENT_NAME": "push", "REF_TYPE": "tag", "REF_NAME": "v0.4.1"},
            {"mode": "release", "version": "0.4.1", "source_sha": "current"},
        ),
        (
            {"EVENT_NAME": "push", "BEFORE_SHA": "before"},
            {"mode": "dev", "version": "", "source_sha": "current"},
        ),
        (
            {"EVENT_NAME": "push", "BEFORE_SHA": "before", "CURRENT_VERSION": "0.5.0"},
            {"mode": "skip", "version": "", "source_sha": "current"},
        ),
    ],
)
def test_docs_classifier_checks_source_version_and_selects_commit(
    tmp_path: Path, overrides: dict[str, str], expected: dict[str, str] | None
) -> None:
    workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    script = textwrap.dedent(workflow.split("        run: |\n", 1)[1].split("\n  validate:")[0])
    output = tmp_path / "outputs"
    env = {
        **os.environ,
        "EVENT_NAME": "workflow_dispatch",
        "REF_TYPE": "branch",
        "REF_NAME": "main",
        "INPUT_VERSION": "",
        "BEFORE_SHA": "",
        "CURRENT_SHA": "current",
        "CURRENT_VERSION": "0.4.1",
        "TAG_VERSION": "0.4.1",
        "LEGACY_TAG": "0",
        "GITHUB_OUTPUT": str(output),
        **overrides,
    }
    result = subprocess.run(
        ["bash", "-c", _GIT + script],
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if expected is None:
        assert result.returncode != 0
        assert not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert dict(line.split("=", 1) for line in output.read_text().splitlines()) == expected
