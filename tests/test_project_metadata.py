from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

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
        "Documentation": "https://github.com/aaronmgn/stonepy/blob/main/docs/API_REFERENCE.md",
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
    assert data["tool"]["hatch"]["version"] == {"path": "src/stonepy/__init__.py"}


def test_runtime_dependencies_have_major_version_caps() -> None:
    project = _pyproject()["project"]
    assert isinstance(project, dict)

    assert project["dependencies"] == [
        "httpx>=0.27,<1.0",
        "pydantic>=2.7,<3.0",
        "simplejson>=3.19,<4.0",
    ]


def test_build_config_scopes_sdist_and_keeps_py_typed() -> None:
    tool = _pyproject()["tool"]
    hatch = tool["hatch"]
    assert hatch["build"]["targets"]["sdist"]["include"] == [
        "src/stonepy",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "pyproject.toml",
    ]
    assert hatch["build"]["targets"]["wheel"]["force-include"] == {
        "src/stonepy/py.typed": "stonepy/py.typed"
    }


def test_coverage_config_does_not_hide_generated_endpoint_or_client_surface() -> None:
    coverage = _pyproject()["tool"]["coverage"]["run"]
    omitted = set(coverage["omit"])

    assert "src/stonepy/_endpoints/*" not in omitted
    assert "src/stonepy/client.py" not in omitted


def test_license_file_exists() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert text.startswith("MIT License")
    assert "Copyright (c) 2026 Aaron Morgan" in text


def test_uv_lock_is_committable_and_ci_uses_frozen_sync() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uv.lock" not in {line.strip() for line in gitignore}
    assert (ROOT / "uv.lock").is_file()
    assert "uv sync --frozen --extra dev" in ci
    assert "uv pip install --system" not in ci


def test_ci_builds_and_checks_distribution_artifacts() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python-version: ["3.11", "3.12", "3.13"]' in ci
    assert "uv build" in ci
    assert "twine check dist/*" in ci


def test_ruff_is_the_only_configured_formatter() -> None:
    data = _pyproject()
    dev_deps = data["project"]["optional-dependencies"]["dev"]
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert all(not dep.startswith("black") for dep in dev_deps)
    assert "black" not in data["tool"]
    assert "uv run ruff format --check ." in ci
    assert "uv run black" not in ci
    assert "ruff format" in pre_commit
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
