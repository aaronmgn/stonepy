from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_project_declares_license_and_pypi_metadata() -> None:
    project = _pyproject()["project"]
    assert isinstance(project, dict)

    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert project["authors"] == [{"name": "Aaron Morgan", "email": "aaron@dvops.io"}]
    assert project["keywords"] == ["stonex", "ciapi", "trading", "cityindex"]
    assert project["urls"] == {
        "Homepage": "https://github.com/aaronmgn/stonepy",
        "Repository": "https://github.com/aaronmgn/stonepy",
        "Documentation": "https://aaronmgn.github.io/stonepy/",
        "Issues": "https://github.com/aaronmgn/stonepy/issues",
        "Changelog": "https://github.com/aaronmgn/stonepy/blob/main/CHANGELOG.md",
    }
    assert "Typing :: Typed" in project["classifiers"]
    # PEP 639: the SPDX `license` expression supersedes the License classifier.
    assert "License :: OSI Approved :: MIT License" not in project["classifiers"]
    assert "Operating System :: OS Independent" in project["classifiers"]
    assert "Programming Language :: Python :: 3 :: Only" in project["classifiers"]


def test_project_version_is_single_sourced_from_package() -> None:
    data = _pyproject()
    project = data["project"]
    assert isinstance(project, dict)

    assert "version" not in project
    assert project["dynamic"] == ["version"]
    assert data["tool"]["hatch"]["version"] == {"path": "src/stonepy/_version.py"}


def test_runtime_dependencies_have_major_version_caps() -> None:
    project = _pyproject()["project"]
    assert isinstance(project, dict)

    deps = project["dependencies"]
    names = [re.split(r"[<>=~!\[; ]", dep, maxsplit=1)[0] for dep in deps]
    assert names == ["httpx", "pydantic", "pydantic", "simplejson"]
    assert deps[1] == 'pydantic>=2.7,<3.0; python_version < "3.14"'
    assert deps[2] == 'pydantic>=2.12,<3.0; python_version >= "3.14"'

    # Published runtime constraints must keep a lower bound and an upper major-version cap,
    # so they stay broad for downstream users but never float past a vetted major.
    for dep in deps:
        assert ">=" in dep or "==" in dep, f"{dep} is missing a lower bound"
        assert "<" in dep, f"{dep} is missing an upper major-version cap"


def test_build_config_scopes_sdist() -> None:
    tool = _pyproject()["tool"]
    hatch = tool["hatch"]
    assert hatch["build"]["targets"]["sdist"]["include"] == [
        "/src/stonepy",
        "/README.md",
        "/LICENSE",
        "/CHANGELOG.md",
        "/pyproject.toml",
    ]
    assert "force-include" not in hatch["build"]["targets"]["wheel"]
    assert (ROOT / "src" / "stonepy" / "py.typed").is_file()


def test_coverage_config_does_not_hide_generated_endpoint_or_client_surface() -> None:
    coverage = _pyproject()["tool"]["coverage"]["run"]
    assert coverage["source"] == [
        "src/stonepy/_core",
        "src/stonepy/_generator",
        "src/stonepy/resources",
        "src/stonepy/_endpoints",
    ]
    assert "stonepy.client" in coverage["source_pkgs"]
    assert not any(entry.endswith(".py") for entry in coverage["source"])
    assert _pyproject()["tool"]["coverage"]["report"]["fail_under"] == 90
    omitted = set(coverage["omit"])

    assert "src/stonepy/_endpoints/*" not in omitted
    assert "src/stonepy/client.py" not in omitted


def test_license_file_exists() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 Aaron Morgan" in text


def test_coverage_measures_branches() -> None:
    run = _pyproject()["tool"]["coverage"]["run"]
    assert run["branch"] is True


def test_uv_lock_is_committable_and_ci_uses_locked_sync() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv.lock" not in {line.strip() for line in gitignore}
    assert (ROOT / "uv.lock").is_file()
    assert "uv sync --locked --extra dev" in ci
    assert "--frozen" not in ci
    for workflow in ("live", "docs", "drift"):
        text = (ROOT / ".github" / "workflows" / f"{workflow}.yml").read_text(encoding="utf-8")
        assert "--frozen" not in text
    assert "uv pip install --system" not in ci


def test_ci_builds_and_checks_distribution_artifacts() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python-version: ["3.11", "3.12", "3.13", "3.14"]' in ci
    assert "uv build" in ci
    assert "twine check dist/*" in ci
    assert 'version: "0.12.10"' in ci
    assert "actions/setup-python" not in ci
    assert "python -m stonepy._generator client" in ci
    assert "lowest-direct" in ci
    assert "wheel-smoke" in ci
    assert "workflow_call:" in ci
    lowest = ci.split("  lowest-direct:\n", 1)[1].split("  wheel-smoke:\n", 1)[0]
    assert 'project["dependencies"]' in lowest
    assert "--resolution lowest-direct --upgrade -r /tmp/stonepy-lowest-requirements.txt" in lowest
    assert "uv pip install --python .venv-lowest --no-deps ." in lowest
    assert 'expected = "2.12." if sys.version_info >= (3, 14) else "2.7."' in lowest
    assert "assert installed.startswith(expected)" in lowest
    smoke = ci.split("  wheel-smoke:\n", 1)[1].split("  ci:\n", 1)[0]
    assert "cp -R tests/smoke_installed/. /tmp/stonepy-wheel-smoke/" in smoke
    assert "env -u PYTHONPATH STONEPY_SMOKE_INSTALLED=1 ./bin/python -m pytest . " in smoke


def test_warning_and_workflow_policy_is_pinned() -> None:
    pytest_config = _pyproject()["tool"]["pytest"]["ini_options"]
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    live = (ROOT / ".github" / "workflows" / "live.yml").read_text(encoding="utf-8")
    docs = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    drift = (ROOT / ".github" / "workflows" / "drift.yml").read_text(encoding="utf-8")

    assert pytest_config["filterwarnings"] == ["error"]
    assert "on:\n  push:\n    branches: [main]\n  pull_request:\n  workflow_call:" in ci
    assert "permissions:\n  contents: read" in ci
    assert (
        "concurrency:\n"
        "  group: ci-${{ github.event.pull_request.number || github.ref }}\n"
        "  cancel-in-progress: true" in ci
    )
    repository_guard = "if: github.repository == 'aaronmgn/stonepy'"
    assert repository_guard in drift
    assert repository_guard in live
    assert "permissions:\n  contents: read" in live
    assert 'STONEX_LIVE: "1"' in live
    assert docs.count("contents: write") == 1
    assert (
        "  deploy:\n"
        "    needs: [plan, validate]\n"
        "    if: needs.plan.outputs.mode != 'skip'\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      contents: write\n"
        "      pages: write\n"
        "      id-token: write" in docs
    )
    assert "permissions:\n  contents: read" in docs
    assert "  validate:\n    needs: plan\n" in docs
    assert docs.count("ref: ${{ needs.plan.outputs.source_sha }}") == 2
    assert 'git rev-parse -q --verify "refs/tags/v${INPUT_VERSION}^{commit}"' in docs
    assert 'test "$(version_at "$SHA")" = "${INPUT_VERSION}"' in docs
    assert "uv run --locked mkdocs build --strict" in docs
    assert "strict: true" in (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in drift
    assert "name: catalog-backed consistency lint" in drift
    assert "uv run python scripts/consistency_lint.py" in drift


def test_third_party_workflow_actions_are_pinned_to_commit_shas() -> None:
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        references = re.findall(
            r"^\s*(?:-\s+)?uses:\s*['\"]?([^'\"\s#]+)",
            path.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        assert references, f"{path.name}: no action references found"
        for reference in references:
            if reference.startswith("./"):
                continue
            _, separator, ref = reference.rpartition("@")
            assert separator and re.fullmatch(r"[0-9a-f]{40}", ref), (
                f"{path.name}: action must be pinned to a full commit SHA: {reference}"
            )


def test_release_workflow_is_gated_and_publishes_verified_artifact() -> None:
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    verify, publish = release.split("  publish:\n")
    assert "uses: ./.github/workflows/ci.yml" in release
    assert "    needs: ci\n" in verify
    assert "    needs: verify\n" in publish
    assert "actions/upload-artifact@" in verify
    assert "actions/download-artifact@" in publish
    assert "    permissions:\n      contents: read\n" in verify
    assert "    permissions:\n      contents: read\n      id-token: write" in publish
    assert "uv build" not in publish
    assert "check_release_artifacts.py" in verify


def test_ruff_is_the_only_configured_formatter() -> None:
    data = _pyproject()
    dev_deps = data["project"]["optional-dependencies"]["dev"]
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert all(not dep.startswith("black") for dep in dev_deps)
    assert "black" not in data["tool"]
    assert "uv run --locked ruff format --check ." in ci
    assert "uv run black" not in ci
    assert "uv run --locked ruff format" in pre_commit
    assert "entry: black" not in pre_commit


def test_user_docs_cover_install_async_errors_pagination_and_reference() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "pip install stonepy" in readme
    assert "Requires Python >= 3.11" in readme
    assert "ClientConfig.from_env()" in readme
    assert "async with AsyncStoneXClient" in readme
    assert "except StoneXError" in readme
    assert "RateLimitError" in readme
    assert "Pagination" in readme
    assert (ROOT / "CHANGELOG.md").is_file()
    assert (ROOT / "docs" / "API_REFERENCE.md").is_file()


def test_version_consumers_use_single_source() -> None:
    import stonepy

    source = (ROOT / "src/stonepy/_version.py").read_text()
    match = re.search(r'^__version__ = "([^\"]+)"$', source, re.MULTILINE)
    assert match is not None
    expected = match.group(1)
    assert stonepy.__version__ == expected
    assert stonepy.ClientConfig(base_url="https://x").user_agent == f"stonepy/{expected}"
    assert "importlib.metadata" not in (ROOT / "src/stonepy/_core/config.py").read_text()


def test_user_agent_ignores_installed_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata

    import stonepy

    def fail_version(distribution_name: str) -> str:
        raise AssertionError("installed metadata must not determine the user agent")

    monkeypatch.setattr(importlib.metadata, "version", fail_version)
    assert stonepy.ClientConfig(base_url="https://x").user_agent == f"stonepy/{stonepy.__version__}"


def test_wheel_intentionally_contains_generator() -> None:
    wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/stonepy"]
    assert not any("_generator" in entry for entry in wheel.get("exclude", []))
    checker = (ROOT / "scripts/check_release_artifacts.py").read_text()
    assert "stonepy/_generator/__init__.py" in checker
