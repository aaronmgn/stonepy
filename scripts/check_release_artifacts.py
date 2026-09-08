"""Verify the distributions that CI hands to the release publisher."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import zipfile
from collections.abc import Sequence
from email.parser import Parser
from pathlib import Path

SDIST_REQUIRED_FILES = (
    "pyproject.toml",
    "CATALOG_VERSION",
    "uv.lock",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
    ".github/workflows/docs.yml",
    ".github/workflows/drift.yml",
    ".github/workflows/live.yml",
    ".github/workflows/release.yml",
    "mkdocs.yml",
    "docs/API_REFERENCE.md",
    "docs/gen_ref_pages.py",
    "scripts/check_release_artifacts.py",
    "scripts/consistency_lint.py",
    "tests/__init__.py",
    "tests/test_release_artifacts.py",
    "tests/test_project_metadata.py",
    "tests/test_live_safety.py",
    "tests/core/test_session.py",
    "tests/core/test_models.py",
    "tests/contract/test_models_roundtrip.py",
    "tests/generator/test_consistency_lint.py",
    "tests/generator/fixtures/endpoints.json",
    "tests/generator/fixtures/data-types.json",
    "tests/generator/fixtures/lookup-codes.json",
    "tests/generator/fixtures/resources/session/log_on.py",
    "tests/generator/fixtures/request_graph/endpoints.json",
    "tests/generator/fixtures/request_graph/data-types.json",
    "tests/generator/fixtures/request_graph/lookup-codes.json",
    "tests/live/conftest.py",
    "tests/live/_safety.py",
    "tests/resources/session/test_log_on.py",
    "tests/smoke_installed/test_installed_wheel.py",
    "tests/typing/consumer_model_constructors.py",
    "tests/typing/from_env_overrides.py",
)
"""Suite entry points and supporting files required for offline source-distribution tests."""


def _version(metadata: bytes) -> str:
    headers = Parser().parsestr(metadata.decode("utf-8"))
    versions = headers.get_all("Version", [])
    if len(versions) != 1 or not isinstance(versions[0], str):
        raise ValueError("artifact metadata must contain exactly one Version header")
    return versions[0]


def _check_model_stubs(members: list[str], prefix: str, artifact: str) -> set[str]:
    model_files = {Path(name).name for name in members if name.startswith(prefix + "models/")}
    runtime = {Path(name).stem for name in model_files if name.endswith(".py")} - {
        "__init__",
        "enums",
    }
    stubs = {Path(name).stem for name in model_files if name.endswith(".pyi")}
    if not runtime or stubs != runtime:
        raise ValueError(
            f"{artifact} model stubs differ: missing={sorted(runtime - stubs)}, "
            f"unexpected={sorted(stubs - runtime)}"
        )
    return stubs


def check_artifacts(
    dist_dir: Path, *, source_version: str, tag: str | None = None
) -> dict[str, str]:
    """Check versions and contents, print wheel members, and hash the verified files.

    Args:
        dist_dir: Directory containing exactly one wheel and one source distribution.
        source_version: Exact version string declared by the source package.
        tag: Optional release tag, allowing one leading ``v``.

    Returns:
        A mapping from each distribution filename to its SHA-256 digest.

    Raises:
        ValueError: Artifact counts, versions, tags, or contents violate release policy.
    """
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("release requires exactly one wheel and one sdist")
    if tag is not None and tag.removeprefix("v") != source_version:
        raise ValueError(f"tag {tag!r} does not match source version {source_version!r}")

    wheel, sdist = wheels[0], sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        print(f"Wheel members ({wheel.name}):")
        for name in members:
            print(name)
        if sum(name.endswith("stonepy/py.typed") for name in members) != 1:
            raise ValueError("wheel must contain exactly one stonepy/py.typed marker")
        if "stonepy/_generator/__init__.py" not in members:
            raise ValueError("wheel must include stonepy/_generator/__init__.py")
        wheel_stubs = _check_model_stubs(members, "stonepy/", "wheel")
        metadata = [name for name in members if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("wheel must contain exactly one METADATA file")
        wheel_version = _version(archive.read(metadata[0]))
        if wheel_version != source_version:
            raise ValueError(
                f"wheel version {wheel_version!r} != source version {source_version!r}"
            )

    with tarfile.open(sdist, "r:gz") as source_archive:
        source_members = source_archive.getmembers()
        if any(".uv-cache" in member.name for member in source_members):
            raise ValueError("sdist must not contain .uv-cache members")
        pkg_info = [
            member
            for member in source_members
            if len(Path(member.name).parts) == 2 and Path(member.name).name == "PKG-INFO"
        ]
        if len(pkg_info) != 1 or not pkg_info[0].isfile():
            raise ValueError("sdist must contain exactly one root PKG-INFO file")
        prefix = f"{Path(pkg_info[0].name).parts[0]}/src/stonepy/"
        source_names = [member.name for member in source_members if member.isfile()]
        if source_names.count(prefix + "py.typed") != 1:
            raise ValueError("sdist must contain exactly one stonepy/py.typed marker")
        if _check_model_stubs(source_names, prefix, "sdist") != wheel_stubs:
            raise ValueError("wheel and sdist model stubs differ")
        metadata_file = source_archive.extractfile(pkg_info[0])
        if metadata_file is None:
            raise ValueError("sdist PKG-INFO is not readable")
        with metadata_file:
            sdist_version = _version(metadata_file.read())
        if sdist_version != source_version:
            raise ValueError(
                f"sdist version {sdist_version!r} != source version {source_version!r}"
            )
        root = Path(pkg_info[0].name).parent
        files = {member.name for member in source_members if member.isfile()}
        missing = [name for name in SDIST_REQUIRED_FILES if (root / name).as_posix() not in files]
        if missing:
            raise ValueError("sdist is missing offline test suite files: " + ", ".join(missing))

    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (wheel, sdist)}


def main(argv: Sequence[str] | None = None) -> int:
    """Validate release artifacts from CLI arguments and print their SHA-256 hashes.

    Args:
        argv: Arguments to parse, or ``None`` to use the process arguments.

    Returns:
        Zero when both distributions pass validation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--tag")
    args = parser.parse_args(argv)
    try:
        hashes = check_artifacts(args.dist_dir, source_version=args.source_version, tag=args.tag)
    except (ValueError, OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(hashes, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
