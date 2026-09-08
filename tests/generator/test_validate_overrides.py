from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from stonepy._core.status import StatusDomain
from stonepy._generator import __main__ as generator_main
from stonepy._generator import catalog as catalog_module
from stonepy._generator import emit_endpoints, emit_models, render
from stonepy._generator.catalog import load_catalog
from stonepy._generator.validate_overrides import (
    _override_tables_for_tests,
    assert_override_consumption,
)

FIX = Path(__file__).parent / "fixtures"

_STALE_TABLE_CASES = (
    (
        emit_endpoints,
        "_UNSPECIFIED_RESPONSE_OVERRIDES",
        frozenset({("missing", "MissingEndpoint")}),
    ),
    (
        emit_endpoints,
        "_OPTIONAL_PARAM_OVERRIDES",
        {("missing", "MissingEndpoint"): frozenset({"missingParam"})},
    ),
    (
        emit_endpoints,
        "_RESPONSE_MODEL_OVERRIDES",
        {("missing", "MissingEndpoint"): "MissingDTO"},
    ),
    (
        emit_endpoints,
        "_STATUS_DOMAIN_OVERRIDES",
        {("missing", "MissingEndpoint"): StatusDomain.NONE},
    ),
    (
        emit_endpoints,
        "_LIST_RESPONSE_OVERRIDES",
        frozenset({("missing", "MissingEndpoint")}),
    ),
    (
        emit_endpoints,
        "_SCALAR_RESPONSE_OVERRIDES",
        {("missing", "MissingEndpoint"): "bool"},
    ),
    (
        emit_endpoints,
        "_PARAM_LOCATION_OVERRIDES",
        {("missing", "MissingEndpoint"): {"missingParam": "query"}},
    ),
    (
        emit_endpoints,
        "_PATH_OVERRIDES",
        {("missing", "MissingEndpoint"): "/missing"},
    ),
    (
        emit_endpoints,
        "_HOST_ROOTED_ENDPOINTS",
        frozenset({("missing", "MissingEndpoint")}),
    ),
    (
        emit_endpoints,
        "_RETRY_SAFE_ENDPOINT_OVERRIDES",
        {("missing", "MissingEndpoint")},
    ),
    (
        emit_endpoints,
        "_RETRY_UNSAFE_ENDPOINT_OVERRIDES",
        {("missing", "MissingEndpoint")},
    ),
    (
        emit_endpoints,
        "_SYNTHETIC_PARAM_TYPE_OVERRIDES",
        {("missing", "MissingEndpoint", "missingParam"): "int"},
    ),
    (
        catalog_module,
        "_ARRAY_PROPERTY_OVERRIDES",
        frozenset({("MissingDTO", "MissingField")}),
    ),
    (
        catalog_module,
        "_ENUM_MEMBER_ADDITIONS",
        {"MissingEnum": ({"name": "Missing", "type": "0", "format": None, "ref": None},)},
    ),
    (
        render,
        "_FIELD_TYPE_OVERRIDES",
        {("MissingDTO", "MissingField"): "int"},
    ),
    (render, "_FIELD_DOC_NOTES", {("MissingDTO", "MissingField"): "note"}),
    (
        emit_models,
        "_FORCE_OPTIONAL_FIELDS",
        {"MissingDTO": {"MissingField"}},
    ),
)


def _clear_override_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    for module, table_name in _override_tables_for_tests():
        current = getattr(module, table_name)
        if isinstance(current, dict):
            empty: object = {}
        elif isinstance(current, frozenset):
            empty = frozenset()
        elif isinstance(current, set):
            empty = set()
        else:
            raise AssertionError(f"unsupported override table type: {type(current)!r}")
        monkeypatch.setattr(module, table_name, empty)


def test_consumption_guard_covers_every_planned_override_table() -> None:
    guarded = {(module.__name__, table_name) for module, table_name in _override_tables_for_tests()}
    expected = {(module.__name__, table_name) for module, table_name, _value in _STALE_TABLE_CASES}

    assert guarded == expected


@pytest.mark.parametrize(
    ("module", "table_name", "stale_value"),
    _STALE_TABLE_CASES,
    ids=[table_name for _module, table_name, _value in _STALE_TABLE_CASES],
)
def test_consumption_guard_rejects_stale_keys_in_every_table(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    table_name: str,
    stale_value: object,
) -> None:
    _clear_override_tables(monkeypatch)
    monkeypatch.setattr(module, table_name, stale_value)

    with pytest.raises(ValueError, match=table_name):
        assert_override_consumption(load_catalog(FIX))


def test_status_domain_guard_exempts_only_two_documented_fixture_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_override_tables(monkeypatch)
    fixture_only = {
        ("order", "GetActiveStopLimitOrder"): StatusDomain.NONE,
        ("order", "GetOpenPosition"): StatusDomain.NONE,
    }
    monkeypatch.setattr(emit_endpoints, "_STATUS_DOMAIN_OVERRIDES", fixture_only)

    assert_override_consumption(load_catalog(FIX))

    monkeypatch.setattr(
        emit_endpoints,
        "_STATUS_DOMAIN_OVERRIDES",
        {**fixture_only, ("order", "AnotherFixtureEndpoint"): StatusDomain.NONE},
    )
    with pytest.raises(ValueError, match="AnotherFixtureEndpoint"):
        assert_override_consumption(load_catalog(FIX))


def test_production_generation_fails_on_doctored_stale_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_override_tables(monkeypatch)
    monkeypatch.setattr(
        emit_endpoints,
        "_PATH_OVERRIDES",
        {("missing", "DoctoredStaleEndpoint"): "/missing"},
    )
    monkeypatch.setattr(generator_main, "assert_catalog_frozen", lambda *_args: None)

    with pytest.raises(ValueError, match="DoctoredStaleEndpoint"):
        generator_main.main(
            [
                "endpoints",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
                "--allow-unresolved",
            ]
        )


def test_allow_unfrozen_catalog_still_validates_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        emit_endpoints,
        "_PATH_OVERRIDES",
        {**emit_endpoints._PATH_OVERRIDES, ("missing", "FixtureOnlyEndpoint"): "/missing"},
    )
    with pytest.raises(ValueError, match="FixtureOnlyEndpoint"):
        generator_main.main(
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
    assert not (tmp_path / "models").exists()


def test_explicit_skip_override_validation_is_required(tmp_path: Path) -> None:
    assert (
        generator_main.main(
            [
                "models",
                "--catalog-root",
                str(FIX),
                "--out-dir",
                str(tmp_path),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
                "--skip-override-validation",
            ]
        )
        == 0
    )
