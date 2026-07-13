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
