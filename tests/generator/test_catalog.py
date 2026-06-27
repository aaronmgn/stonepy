from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from stonepy._generator.catalog import (
    assert_allowed_unresolved,
    assert_catalog_frozen,
    is_enum_record,
    load_catalog,
    python_name,
    python_type,
)

FIX = Path(__file__).parent / "fixtures"


def test_loads_records() -> None:
    cat = load_catalog(FIX)

    assert [endpoint.name for endpoint in cat.endpoints] == [
        "GetActiveStopLimitOrder",
        "CancelOrder",
    ]
    assert cat.endpoints[0].response_type == "GetActiveStopLimitOrderResponseDTOv2"
    assert cat.endpoints[0].raw["response_type"] == "GetActiveStopLimitOrderResponseDTO v2"
    assert {datatype.name for datatype in cat.datatypes} == {
        "AlertDTO",
        "AlertDirection",
        "DanglingRefDTO",
    }
    assert "InstructionStatus" in cat.lookups


def test_load_catalog_accepts_legacy_lookups_filename(
    tmp_path: Path,
) -> None:
    shutil.copy(FIX / "endpoints.json", tmp_path / "endpoints.json")
    shutil.copy(FIX / "data-types.json", tmp_path / "data-types.json")
    shutil.copy(FIX / "lookup-codes.json", tmp_path / "lookups.json")

    cat = load_catalog(tmp_path)

    assert "InstructionStatus" in cat.lookups


def test_detects_enum_shaped_dto() -> None:
    cat = load_catalog(FIX)
    alert = next(d for d in cat.datatypes if d.name == "AlertDirection")

    assert is_enum_record(alert) is True


def test_decimal_maps_to_decimal() -> None:
    assert python_type({"type": "number", "format": "decimal", "ref": None}, set()) == "Decimal"


def test_wcf_date_maps_to_datetime() -> None:
    assert (
        python_type({"type": "string", "format": "wcf-date", "ref": None}, set())
        == "StoneXDateTime"
    )
    assert (
        python_type({"type": "number", "format": "wcf-date", "ref": None}, set())
        == "StoneXDateTime"
    )


def test_dangling_ref_is_unresolved() -> None:
    assert python_type({"type": "Ghost", "format": None, "ref": "Ghost"}, set()) == "Unresolved"


def test_status_type_is_not_treated_as_unresolved() -> None:
    assert python_type({"type": "Status", "format": None, "ref": None}, set()) == "str"


def test_dirty_type_casing_is_normalized() -> None:
    assert python_type({"type": "Integer", "format": None, "ref": None}, set()) == "int"
    assert python_type({"type": "String", "format": None, "ref": None}, set()) == "str"


def test_array_spacing_maps_to_list_of_known_ref() -> None:
    assert (
        python_type(
            {"type": "LegalPartyDTO []", "format": None, "ref": "LegalPartyDTO"},
            {"LegalPartyDTO"},
        )
        == "list[LegalPartyDTO]"
    )


def test_load_catalog_restores_known_array_property_markers(tmp_path: Path) -> None:
    (tmp_path / "endpoints.json").write_text("[]", encoding="utf-8")
    (tmp_path / "lookup-codes.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data-types.json").write_text(
        """
        [
          {
            "name": "GetPriceTickResponseDTO",
            "properties": [
              {
                "name": "PriceTicks",
                "type": "PriceTickDTO",
                "format": null,
                "ref": "PriceTickDTO"
              }
            ]
          },
          {"name": "PriceTickDTO", "properties": []}
        ]
        """,
        encoding="utf-8",
    )

    cat = load_catalog(tmp_path)
    response = next(rec for rec in cat.datatypes if rec.name == "GetPriceTickResponseDTO")

    assert response.raw["properties"][0]["type"] == "PriceTickDTO"
    assert (
        python_type(response.properties[0], {rec.name for rec in cat.datatypes})
        == "list[PriceTickDTO]"
    )


def test_load_catalog_collects_unresolved_property_types() -> None:
    cat = load_catalog(FIX)

    assert {
        "AlertDTO.Comment",
        "ApiTradeOrderResponseDTO",
        "CancelOrderRequestDTO",
        "GetActiveStopLimitOrderResponseDTOv2",
        "Ghost",
        "LegalPartyDTO",
    } <= cat.unresolved
    assert "AlertDTO" not in cat.unresolved


def test_assert_allowed_unresolved_rejects_new_unknowns() -> None:
    cat = load_catalog(FIX)

    try:
        assert_allowed_unresolved(cat, allowed={"Ghost"})
    except ValueError as exc:
        assert "AlertDTO.Comment" in str(exc)
    else:
        raise AssertionError("expected unresolved catalog validation failure")


def test_assert_catalog_frozen_rejects_git_sha_mismatch(tmp_path: Path) -> None:
    cat = load_catalog(FIX)
    version_file = tmp_path / "CATALOG_VERSION"
    version_file.write_text(
        "expected-sha\nendpoints=2 data_types=3 lookups=1\n",
        encoding="utf-8",
    )

    try:
        assert_catalog_frozen(cat, FIX, version_file=version_file, git_sha="actual-sha")
    except ValueError as exc:
        assert "catalog version mismatch" in str(exc)
    else:
        raise AssertionError("expected catalog freeze validation failure")


def test_assert_catalog_frozen_rejects_count_mismatch(tmp_path: Path) -> None:
    cat = load_catalog(FIX)
    version_file = tmp_path / "CATALOG_VERSION"
    version_file.write_text(
        "expected-sha\nendpoints=999 data_types=3 lookups=1\n",
        encoding="utf-8",
    )

    try:
        assert_catalog_frozen(cat, FIX, version_file=version_file, git_sha="expected-sha")
    except ValueError as exc:
        assert "catalog count mismatch" in str(exc)
    else:
        raise AssertionError("expected catalog count validation failure")


def test_assert_catalog_frozen_rejects_dirty_catalog_files(tmp_path: Path) -> None:
    catalog_root = tmp_path / "catalog"
    catalog_root.mkdir()
    for filename in ("endpoints.json", "data-types.json", "lookup-codes.json"):
        shutil.copy(FIX / filename, catalog_root / filename)

    subprocess.run(["git", "init"], cwd=catalog_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=catalog_root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "freeze catalog",
        ],
        cwd=catalog_root,
        check=True,
        capture_output=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=catalog_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    version_file = tmp_path / "CATALOG_VERSION"
    version_file.write_text(
        f"{sha}\nendpoints=2 data_types=3 lookups=1\n",
        encoding="utf-8",
    )
    cat = load_catalog(catalog_root)
    (catalog_root / "endpoints.json").write_text(
        (catalog_root / "endpoints.json")
        .read_text(encoding="utf-8")
        .replace(
            "Queries for an active stop limit order",
            "DIRTY: Queries for an active stop limit order",
        ),
        encoding="utf-8",
    )

    try:
        assert_catalog_frozen(cat, catalog_root, version_file=version_file)
    except ValueError as exc:
        assert "catalog files are dirty" in str(exc)
    else:
        raise AssertionError("expected dirty catalog validation failure")


def test_modifier_suffixes_are_normalized() -> None:
    assert (
        python_type({"type": "integer required True", "format": None, "ref": None}, set()) == "int"
    )
    assert (
        python_type({"type": "string[] nullable true", "format": None, "ref": None}, set())
        == "list[str]"
    )
    assert (
        python_type({"type": "boolean required false", "format": None, "ref": None}, set())
        == "bool"
    )
    assert (
        python_type({"type": "long integer nullable true", "format": None, "ref": None}, set())
        == "int"
    )


def test_number_without_decimal_format_stays_lossless() -> None:
    assert python_type({"type": "number", "format": None, "ref": None}, set()) == "Decimal"
    assert python_type({"type": "number", "format": "long", "ref": None}, set()) == "int"


def test_versioned_type_names_are_python_safe() -> None:
    assert python_name("ApiLogOnResponseDTO v2") == "ApiLogOnResponseDTOv2"
    assert python_name("class") == "class_"
    assert (
        python_type(
            {
                "type": "ApiTradingAccountDTO v2",
                "format": None,
                "ref": "ApiTradingAccountDTO v2",
            },
            {"ApiTradingAccountDTOv2"},
        )
        == "ApiTradingAccountDTOv2"
    )
