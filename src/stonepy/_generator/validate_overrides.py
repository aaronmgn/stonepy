"""Validate that every curated generator override still matches the catalog."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from types import ModuleType
from typing import Final

import stonepy._generator.catalog as catalog_module
import stonepy._generator.emit_endpoints as emit_endpoints
import stonepy._generator.emit_models as emit_models
import stonepy._generator.render as render_module
from stonepy._generator.catalog import Catalog, EndpointRecord, JsonObject, TypeRecord

_DIRECT_ENDPOINT_TABLES: Final[tuple[str, ...]] = (
    "_OPTIONAL_PARAM_OVERRIDES",
    "_RESPONSE_MODEL_OVERRIDES",
    "_STATUS_DOMAIN_OVERRIDES",
    "_LIST_RESPONSE_OVERRIDES",
    "_SCALAR_RESPONSE_OVERRIDES",
    "_UNSPECIFIED_RESPONSE_OVERRIDES",
    "_PARAM_LOCATION_OVERRIDES",
    "_PATH_OVERRIDES",
    "_HOST_ROOTED_ENDPOINTS",
    "_RETRY_UNSAFE_ENDPOINT_OVERRIDES",
)
_STATUS_DOMAIN_FIXTURE_ONLY_KEYS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("order", "GetActiveStopLimitOrder"),
        ("order", "GetOpenPosition"),
    }
)


def assert_override_consumption(catalog: Catalog) -> None:
    """Raise when a curated override no longer matches the production catalog."""

    errors: list[str] = []
    endpoints = {
        (emit_endpoints.target_module(rec.target), rec.name): rec for rec in catalog.endpoints
    }
    datatypes = {rec.name: rec for rec in catalog.datatypes}

    for table_name in _DIRECT_ENDPOINT_TABLES:
        table = getattr(emit_endpoints, table_name)
        keys = set(_table_keys(table))
        if table_name == "_STATUS_DOMAIN_OVERRIDES":
            keys -= _STATUS_DOMAIN_FIXTURE_ONLY_KEYS
        _check_endpoint_keys(errors, f"emit_endpoints.{table_name}", keys, endpoints)

    retry_safe_keys = {
        (
            emit_endpoints.target_module(rec.target),
            rec.logical_name or emit_endpoints._VERSION_SUFFIX_RE.sub("", rec.name),
        )
        for rec in catalog.endpoints
    }
    _check_keys(
        errors,
        "emit_endpoints._RETRY_SAFE_ENDPOINT_OVERRIDES",
        set(emit_endpoints._RETRY_SAFE_ENDPOINT_OVERRIDES),
        retry_safe_keys,
        "catalog endpoint logical name",
    )

    _check_endpoint_parameter_names(
        errors,
        "emit_endpoints._OPTIONAL_PARAM_OVERRIDES",
        emit_endpoints._OPTIONAL_PARAM_OVERRIDES,
        endpoints,
    )
    _check_endpoint_parameter_names(
        errors,
        "emit_endpoints._PARAM_LOCATION_OVERRIDES",
        emit_endpoints._PARAM_LOCATION_OVERRIDES,
        endpoints,
    )
    _check_synthetic_param_types(errors, endpoints)
    _check_array_properties(errors, datatypes)
    _check_enum_additions(errors, datatypes)
    _check_field_types(errors, datatypes)
    _check_force_optional_fields(errors, datatypes)

    if errors:
        details = "\n".join(f"- {error}" for error in sorted(errors))
        raise ValueError(f"unconsumed generator overrides:\n{details}")


def _table_keys(table: object) -> Collection[tuple[str, str]]:
    if isinstance(table, Mapping):
        return table.keys()
    return table  # type: ignore[return-value]


def _check_endpoint_keys(
    errors: list[str],
    table_name: str,
    keys: set[tuple[str, str]],
    endpoints: Mapping[tuple[str, str], EndpointRecord],
) -> None:
    _check_keys(errors, table_name, keys, set(endpoints), "catalog endpoint")


def _check_keys(
    errors: list[str],
    table_name: str,
    keys: set[tuple[str, str]],
    available: set[tuple[str, str]],
    expected: str,
) -> None:
    for key in sorted(keys - available):
        errors.append(f"{table_name} key {key!r} does not match a {expected}")


def _check_endpoint_parameter_names(
    errors: list[str],
    table_name: str,
    table: Mapping[tuple[str, str], Collection[str] | Mapping[str, str]],
    endpoints: Mapping[tuple[str, str], EndpointRecord],
) -> None:
    for endpoint_key, overridden_names in table.items():
        rec = endpoints.get(endpoint_key)
        if rec is None:
            continue
        catalog_names = {
            name for param in rec.parameters if isinstance((name := param.get("name")), str)
        }
        for name in sorted(set(overridden_names) - catalog_names):
            errors.append(
                f"{table_name} key {endpoint_key!r} names missing catalog parameter {name!r}"
            )


def _check_synthetic_param_types(
    errors: list[str],
    endpoints: Mapping[tuple[str, str], EndpointRecord],
) -> None:
    table_name = "emit_endpoints._SYNTHETIC_PARAM_TYPE_OVERRIDES"
    for (
        target,
        endpoint_name,
        placeholder,
    ), _annotation in emit_endpoints._SYNTHETIC_PARAM_TYPE_OVERRIDES.items():
        endpoint_key = (target, endpoint_name)
        rec = endpoints.get(endpoint_key)
        if rec is None:
            errors.append(f"{table_name} key {(target, endpoint_name, placeholder)!r} is stale")
            continue
        placeholders = set(
            emit_endpoints._PLACEHOLDER_RE.findall(emit_endpoints.resolved_path(rec))
        )
        declared_names = {
            name.lower() for param in rec.parameters if isinstance((name := param.get("name")), str)
        }
        if placeholder not in placeholders or placeholder.lower() in declared_names:
            errors.append(
                f"{table_name} key {(target, endpoint_name, placeholder)!r} "
                "does not match an undeclared endpoint placeholder"
            )


def _check_array_properties(errors: list[str], datatypes: Mapping[str, TypeRecord]) -> None:
    table_name = "catalog._ARRAY_PROPERTY_OVERRIDES"
    for key in sorted(catalog_module._ARRAY_PROPERTY_OVERRIDES):
        rec, prop = _raw_property(datatypes, key)
        if rec is None or prop is None:
            errors.append(f"{table_name} key {key!r} does not match a catalog property")
            continue
        raw_type = prop.get("type")
        if not isinstance(raw_type, str) or catalog_module._parse_type(raw_type)[1]:
            errors.append(f"{table_name} key {key!r} no longer needs an array correction")


def _check_enum_additions(errors: list[str], datatypes: Mapping[str, TypeRecord]) -> None:
    table_name = "catalog._ENUM_MEMBER_ADDITIONS"
    for owner, additions in catalog_module._ENUM_MEMBER_ADDITIONS.items():
        rec = datatypes.get(owner)
        if rec is None:
            errors.append(f"{table_name} key {owner!r} does not match a catalog datatype")
            continue
        raw_properties = _raw_properties(rec)
        for addition in additions:
            addition_name = addition.get("name")
            addition_code = addition.get("type")
            if any(
                prop.get("name") == addition_name or prop.get("type") == addition_code
                for prop in raw_properties
            ):
                errors.append(
                    f"{table_name} key {(owner, addition_name, addition_code)!r} "
                    "duplicates a catalog enum member"
                )


def _check_field_types(errors: list[str], datatypes: Mapping[str, TypeRecord]) -> None:
    table_name = "render._FIELD_TYPE_OVERRIDES"
    for key in sorted(render_module._FIELD_TYPE_OVERRIDES):
        rec, prop = _raw_property(datatypes, key)
        if rec is None or prop is None:
            errors.append(f"{table_name} key {key!r} does not match a catalog property")


def _check_force_optional_fields(errors: list[str], datatypes: Mapping[str, TypeRecord]) -> None:
    table_name = "emit_models._FORCE_OPTIONAL_FIELDS"
    for owner, field_names in emit_models._FORCE_OPTIONAL_FIELDS.items():
        rec = datatypes.get(owner)
        if rec is None:
            errors.append(f"{table_name} key {owner!r} does not match a catalog datatype")
            continue
        catalog_names = {
            name for prop in _raw_properties(rec) if isinstance((name := prop.get("name")), str)
        }
        for field_name in sorted(field_names - catalog_names):
            errors.append(f"{table_name} key {(owner, field_name)!r} is not a catalog property")


def _raw_property(
    datatypes: Mapping[str, TypeRecord], key: tuple[str, str]
) -> tuple[TypeRecord | None, JsonObject | None]:
    owner, field_name = key
    rec = datatypes.get(owner)
    if rec is None:
        return None, None
    prop = next((prop for prop in _raw_properties(rec) if prop.get("name") == field_name), None)
    return rec, prop


def _raw_properties(rec: TypeRecord) -> list[JsonObject]:
    properties = rec.raw.get("properties")
    if not isinstance(properties, list):
        return []
    return [prop for prop in properties if isinstance(prop, dict)]


def _override_tables_for_tests() -> tuple[tuple[ModuleType, str], ...]:
    """Return every consumption-guarded table for focused generator tests."""

    return (
        *((emit_endpoints, name) for name in _DIRECT_ENDPOINT_TABLES),
        (emit_endpoints, "_RETRY_SAFE_ENDPOINT_OVERRIDES"),
        (emit_endpoints, "_SYNTHETIC_PARAM_TYPE_OVERRIDES"),
        (catalog_module, "_ARRAY_PROPERTY_OVERRIDES"),
        (catalog_module, "_ENUM_MEMBER_ADDITIONS"),
        (render_module, "_FIELD_TYPE_OVERRIDES"),
        (emit_models, "_FORCE_OPTIONAL_FIELDS"),
    )
