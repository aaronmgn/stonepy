from __future__ import annotations

from pathlib import Path

from scripts.consistency_lint import check_resources


def test_consistency_lint_accepts_resource_mixin(tmp_path: Path) -> None:
    resource = tmp_path / "resources" / "session" / "log_on.py"
    resource.parent.mkdir(parents=True)
    resource.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from stonepy._core.resource import BaseResource",
                "",
                "",
                "class _LogOnMixin(BaseResource):",
                "    async def log_on(self) -> object:",
                "        return object()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert check_resources(tmp_path / "resources") == []


def test_consistency_lint_rejects_wrong_method_name(tmp_path: Path) -> None:
    resource = tmp_path / "resources" / "session" / "log_on.py"
    resource.parent.mkdir(parents=True)
    resource.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from stonepy._core.resource import BaseResource",
                "",
                "",
                "class _LogOnMixin(BaseResource):",
                "    async def authenticate(self) -> object:",
                "        return object()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    errors = check_resources(tmp_path / "resources")

    assert errors == [f"{resource}: public method must be named log_on"]


def test_ci_runs_consistency_lint_and_handwritten_coverage_gate() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "uv run python scripts/consistency_lint.py" in text
    assert "--cov=src/stonepy/_core" in text
    assert "--cov=src/stonepy/_generator" in text
    assert "--cov=src/stonepy/resources" in text

    coverage_config = (Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    assert '"src/stonepy/resources/*/_sync/*"' in coverage_config
    assert '"src/stonepy/resources/*/__init__.py"' in coverage_config
