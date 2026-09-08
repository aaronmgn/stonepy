from pathlib import Path

import pytest

from stonepy._generator.__main__ import main

FIX = Path(__file__).parent / "fixtures"


def test_cli_requires_catalog_flag_or_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("STONEPY_CATALOG", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main(["models", "--out-dir", str(tmp_path)])

    assert exc_info.value.code == 2
    error = capsys.readouterr().err
    assert "--catalog-root" in error
    assert "STONEPY_CATALOG" in error


def test_cli_uses_catalog_environment_when_flag_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STONEPY_CATALOG", str(FIX))

    assert (
        main(
            [
                "models",
                "--out-dir",
                str(tmp_path),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
            ]
        )
        == 0
    )

    assert (tmp_path / "models" / "AlertDTO.py").exists()


def test_cli_catalog_flag_takes_precedence_over_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STONEPY_CATALOG", str(tmp_path / "missing"))

    assert (
        main(
            [
                "models",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
            ]
        )
        == 0
    )

    assert (tmp_path / "models" / "AlertDTO.py").exists()


@pytest.mark.parametrize("response_type", ["UnknownDTO", None])
def test_cli_unresolved_response_preflight_preserves_endpoint_tree(
    tmp_path: Path, response_type: str | None
) -> None:
    import json
    import shutil

    catalog_root = tmp_path / "catalog"
    shutil.copytree(FIX, catalog_root)
    endpoints = json.loads((catalog_root / "endpoints.json").read_text())
    endpoints[0]["response_type"] = response_type
    (catalog_root / "endpoints.json").write_text(json.dumps(endpoints))
    package_dir = tmp_path / "stonepy"
    sentinel = package_dir / "_endpoints" / "sentinel.py"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("# keep me")
    model_sentinel = package_dir / "models" / "sentinel.py"
    model_sentinel.parent.mkdir()
    model_sentinel.write_text("# keep models too")
    with pytest.raises(ValueError, match=response_type or "no response type or reviewed override"):
        main(
            [
                "all",
                "--catalog-root",
                str(catalog_root),
                "--package-dir",
                str(package_dir),
                "--project-root",
                str(tmp_path),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
            ]
        )
    assert sentinel.read_text() == "# keep me"
    assert model_sentinel.read_text() == "# keep models too"
