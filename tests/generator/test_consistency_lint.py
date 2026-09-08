from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts import consistency_lint
from scripts.consistency_lint import check_resources

FIX = Path(__file__).parent / "fixtures"


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


@pytest.mark.parametrize("catalog_env", [None, "", "   "])
def test_consistency_lint_loudly_skips_catalog_when_environment_is_blank(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    catalog_env: str | None,
) -> None:
    if catalog_env is None:
        monkeypatch.delenv("STONEPY_CATALOG", raising=False)
    else:
        monkeypatch.setenv("STONEPY_CATALOG", catalog_env)

    result = consistency_lint.main([str(tmp_path / "resources")])

    assert result == 0
    assert capsys.readouterr().err == "catalog checks SKIPPED (STONEPY_CATALOG not set)\n"


def test_consistency_lint_reports_broken_catalog_root_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalog_root = tmp_path / "broken-catalog"
    catalog_root.mkdir()
    monkeypatch.setenv("STONEPY_CATALOG", str(catalog_root))

    result = consistency_lint.main([str(tmp_path / "resources")])
    error = capsys.readouterr().err

    assert result == 1
    assert "catalog checks ERROR" in error
    assert "missing required file(s)" in error
    assert "endpoints.json" in error
    assert "data-types.json" in error
    assert "Traceback" not in error


def test_consistency_lint_accepts_valid_catalog_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    for filename in ("endpoints.json", "data-types.json", "lookup-codes.json"):
        shutil.copy(FIX / filename, catalog_root / filename)
    monkeypatch.setenv("STONEPY_CATALOG", str(catalog_root))
    monkeypatch.setattr(consistency_lint, "assert_allowed_unresolved", lambda _catalog: None)
    monkeypatch.setattr(
        consistency_lint,
        "assert_catalog_frozen",
        lambda _catalog, _catalog_root: None,
    )

    result = consistency_lint.main([str(tmp_path / "resources")])

    assert result == 0
    assert capsys.readouterr().err == ""


def test_consistency_lint_has_no_hardcoded_home_catalog_path() -> None:
    source = (Path(__file__).parents[2] / "scripts/consistency_lint.py").read_text(encoding="utf-8")

    assert "/home/aaron" not in source


def test_ci_runs_consistency_lint_and_handwritten_coverage_gate() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "uv run --locked python scripts/consistency_lint.py" in text
    assert "uv run --locked pytest --cov" in text

    coverage_config = (Path(__file__).parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    assert '"src/stonepy/resources/*/_sync/*"' in coverage_config
    assert '"src/stonepy/resources/*/__init__.py"' in coverage_config
