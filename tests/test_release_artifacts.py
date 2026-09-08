from __future__ import annotations

import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release_artifacts import SDIST_REQUIRED_FILES, check_artifacts, main


def _artifacts(
    dist_dir: Path,
    *,
    wheel_version: str = "0.4.1",
    sdist_version: str = "0.4.1",
    wheel_extra: tuple[str, ...] = (),
    sdist_extra: tuple[str, ...] = (),
    omit: str | None = None,
) -> tuple[Path, Path]:
    wheel = dist_dir / "stonepy-0.4.1-py3-none-any.whl"
    sdist = dist_dir / "stonepy-0.4.1.tar.gz"
    wheel_members = {
        "stonepy/__init__.py": b"",
        "stonepy/py.typed": b"",
        "stonepy/models/ExampleDTO.py": b"",
        "stonepy/models/ExampleDTO.pyi": b"",
        "stonepy/_generator/__init__.py": b"",
        "stonepy-0.4.1.dist-info/METADATA": f"Name: stonepy\nVersion: {wheel_version}\n".encode(),
    }
    wheel_members.update(dict.fromkeys(wheel_extra, b""))
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in wheel_members.items():
            if name != omit:
                archive.writestr(name, content)
    source_members = {
        "stonepy-0.4.1/PKG-INFO": f"Name: stonepy\nVersion: {sdist_version}\n".encode(),
        "stonepy-0.4.1/src/stonepy/__init__.py": b"",
        "stonepy-0.4.1/src/stonepy/py.typed": b"",
        "stonepy-0.4.1/src/stonepy/models/ExampleDTO.py": b"",
        "stonepy-0.4.1/src/stonepy/models/ExampleDTO.pyi": b"",
    }
    source_members.update(dict.fromkeys((f"stonepy-0.4.1/{p}" for p in SDIST_REQUIRED_FILES), b""))
    source_members.update(dict.fromkeys(sdist_extra, b""))
    with tarfile.open(sdist, "w:gz") as source_archive:
        for name, content in source_members.items():
            if name != omit:
                member = tarfile.TarInfo(name)
                member.size = len(content)
                source_archive.addfile(member, io.BytesIO(content))
    return wheel, sdist


@pytest.mark.parametrize("artifact", ["wheel", "sdist"])
def test_release_artifacts_reject_version_mismatch(tmp_path: Path, artifact: str) -> None:
    _artifacts(
        tmp_path,
        wheel_version="0.5.0" if artifact == "wheel" else "0.4.1",
        sdist_version="0.5.0" if artifact == "sdist" else "0.4.1",
    )
    with pytest.raises(ValueError, match=f"{artifact} version"):
        check_artifacts(tmp_path, source_version="0.4.1")


@pytest.mark.parametrize("tag", ["v0.5.0", "vv0.4.1", "v0.4.1.0", "V0.4.1"])
def test_release_artifacts_reject_tag_mismatch(tmp_path: Path, tag: str) -> None:
    _artifacts(tmp_path)
    with pytest.raises(ValueError, match="tag"):
        check_artifacts(tmp_path, source_version="0.4.1", tag=tag)


@pytest.mark.parametrize("tag", [None, "v0.4.1", "0.4.1"])
def test_release_artifacts_have_clean_contents(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tag: str | None
) -> None:
    wheel, sdist = _artifacts(tmp_path)
    hashes = check_artifacts(tmp_path, source_version="0.4.1", tag=tag)
    assert hashes == {
        wheel.name: hashlib.sha256(wheel.read_bytes()).hexdigest(),
        sdist.name: hashlib.sha256(sdist.read_bytes()).hexdigest(),
    }
    output = capsys.readouterr().out
    with zipfile.ZipFile(wheel) as archive:
        assert output.splitlines()[1:] == archive.namelist()


@pytest.mark.parametrize("artifact", ["wheel", "sdist"])
@pytest.mark.parametrize("count", [0, 2])
def test_release_artifacts_require_exactly_one_wheel_and_sdist(
    tmp_path: Path, artifact: str, count: int
) -> None:
    wheel, sdist = _artifacts(tmp_path)
    path = wheel if artifact == "wheel" else sdist
    if count == 0:
        path.unlink()
    else:
        path.with_name(f"extra-{path.name}").write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="exactly one wheel and one sdist"):
        check_artifacts(tmp_path, source_version="0.4.1")


@pytest.mark.parametrize(
    ("omit", "message"),
    [
        ("stonepy/py.typed", "py.typed"),
        ("stonepy/models/ExampleDTO.pyi", "wheel model stubs"),
        ("stonepy-0.4.1/src/stonepy/models/ExampleDTO.pyi", "sdist model stubs"),
        ("stonepy-0.4.1/src/stonepy/py.typed", "py.typed"),
        ("stonepy/_generator/__init__.py", "_generator"),
        ("stonepy-0.4.1.dist-info/METADATA", "METADATA"),
        ("stonepy-0.4.1/PKG-INFO", "PKG-INFO"),
    ],
)
def test_release_artifacts_require_package_members(tmp_path: Path, omit: str, message: str) -> None:
    _artifacts(tmp_path, omit=omit)
    with pytest.raises(ValueError, match=message):
        check_artifacts(tmp_path, source_version="0.4.1")


@pytest.mark.parametrize("required", SDIST_REQUIRED_FILES)
def test_sdist_requires_offline_suite_and_supporting_files(tmp_path: Path, required: str) -> None:
    _artifacts(tmp_path, omit=f"stonepy-0.4.1/{required}")
    with pytest.raises(ValueError, match="missing offline test suite files") as exc_info:
        check_artifacts(tmp_path, source_version="0.4.1")
    assert required in str(exc_info.value)


@pytest.mark.parametrize(
    ("wheel_extra", "sdist_extra", "message"),
    [
        (("duplicate/stonepy/py.typed",), (), "py.typed"),
        (("stonepy/models/Unexpected.pyi",), (), "wheel model stubs"),
        ((), ("stonepy-0.4.1/src/stonepy/models/Unexpected.pyi",), "sdist model stubs"),
        (("extra.dist-info/METADATA",), (), "METADATA"),
        ((), ("extra/PKG-INFO",), "PKG-INFO"),
        ((), ("stonepy-0.4.1/.uv-cache/wheels/foo",), ".uv-cache"),
        (("stonepy/.stonepy-generate-crash/previous/models/Old.py",), (), "recovery workspaces"),
        (
            (),
            ("stonepy-0.4.1/src/stonepy/.stonepy-generate-crash/new/file.py",),
            "recovery workspaces",
        ),
        ((), ("stonepy-0.4.1/scripts/benchmark_client_construction.py",), "development-only"),
    ],
)
def test_release_artifacts_reject_unclean_contents(
    tmp_path: Path, wheel_extra: tuple[str, ...], sdist_extra: tuple[str, ...], message: str
) -> None:
    _artifacts(tmp_path, wheel_extra=wheel_extra, sdist_extra=sdist_extra)
    with pytest.raises(ValueError, match=message):
        check_artifacts(tmp_path, source_version="0.4.1")


def test_release_artifacts_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    wheel, sdist = _artifacts(tmp_path)
    assert main([str(tmp_path), "--source-version", "0.4.1", "--tag", "v0.4.1"]) == 0
    output = capsys.readouterr().out
    assert set(json.loads(output[output.index("{") :])) == {wheel.name, sdist.name}
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path), "--source-version", "0.5.0"])
    assert exc_info.value.code == 2
    assert "wheel version" in capsys.readouterr().err
