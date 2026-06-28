"""Catalog loading and type normalization for the generator."""

from __future__ import annotations

import json
import keyword
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, cast

CATALOG_VERSION_FILE: Final[Path] = Path(__file__).resolve().parents[3] / "CATALOG_VERSION"

JsonObject = dict[str, Any]

_ARRAY_MARKER_RE = re.compile(r"\s*\[\]\s*")
_PYTHON_NAME_PART_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")
_DIRTY_TYPE_ALIASES: Final[dict[str, str]] = {
    "date": "wcf-date",
    "decimal": "decimal",
    "datetime": "wcf-date",
    "integer": "integer",
    "long": "integer",
    "long integer": "integer",
    "number": "number",
    "string": "string",
    "status": "string",
    "boolean": "boolean",
    # Some v2 data types (e.g. ApiAccountOperatorsDTO v2, ApiRestrictionsDTO v2) spell the
    # boolean primitive ``bool``; treat it as the catalog's canonical ``boolean``.
    "bool": "boolean",
}
# ``LinkedAccountResult`` ships five properties with empty name/type/ref in the catalog, which
# normalize to the ``Unresolved`` sentinel. The page documents no usable field shape, so this is
# a declared catalog gap rather than a generator bug; allow it through the resolution gate.
DEFAULT_ALLOWED_UNRESOLVED: Final[frozenset[str]] = frozenset({"Unresolved"})
_PRIMITIVE_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "integer",
        "number",
        "decimal",
        "wcf-date",
        "boolean",
        "string",
    }
)
_ARRAY_PROPERTY_OVERRIDES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("AllocationProfileDTO", "Entries"),
        ("ApiAdvisoryTradeOrderResponseDTO", "ManagedInstructions"),
        ("ApiBandedSpreadsDTO", "Prices"),
        ("ApiBandedSpreadsDTO", "SpreadBands"),
        ("ApiClientApplicationMessageTranslationResponseDTO", "TranslationKeyValuePairs"),
        ("ApiConnectUserDetailsDTO", "UserTradingAccounts"),
        ("ApiGetPreferencesResponseDTO", "Preferences"),
        ("ApiLookupResponseDTO", "ApiCultureLookupDTOList"),
        ("ApiLookupResponseDTO", "ApiLookupDTOList"),
        ("ApiManagedClientAccountsMarginResponseDTO", "ClientAccountsMargin"),
        ("ApiManagedInstructionResponseDTO", "Orders"),
        ("ApiMarketInformationDTOv2", "MarketBreakTimes"),
        ("ApiMarketInformationDTOv2", "MarketEod"),
        ("ApiMarketInformationDTOv2", "MarketPricingTimes"),
        ("ApiOpenPositionDTOv2", "ManagedTrades"),
        ("ApiOrderDTOv2", "IfDone"),
        ("ApiOrderResponseDTO", "IfDone"),
        ("ApiProductInformationDTO", "AdditionalMarketSpreads"),
        ("ApiProductInformationDTO", "Bands"),
        ("ApiSaveClientPreferenceRequestDTO", "ClientPreference"),
        ("ApiSavePreferencesRequestDTO", "Preferences"),
        ("ApiSimulateTradeOrderResponseDTO", "Orders"),
        ("ApiTradeOrderDTOv2", "ManagedTrades"),
        ("ApiTradeOrderResponseDTO", "Actions"),
        ("ApiTradeOrderResponseDTO", "Orders"),
        ("ApiUserFollowedUsersDTO", "FollowedUsers"),
        ("ApiUserFollowersDTO", "Followers"),
        ("ApiWallItemsForUsersDTO", "WallItemsForUser"),
        ("FullMarketInformationSearchWithTagsResponseDTOv2", "MarketInformation"),
        ("FullMarketInformationSearchWithTagsResponseDTOv2", "Tags"),
        ("GetPriceBarResponseDTO", "PriceBars"),
        ("GetPriceTickResponseDTO", "PriceTicks"),
        ("ListActiveOrdersResponseDTO", "ActiveOrders"),
        ("ListActiveStopLimitOrderResponseDTO", "ActiveStopLimitOrders"),
        ("ListAllocationProfilesResponseDTO", "AllocationProfiles"),
        ("ListCfdMarketsResponseDTO", "Markets"),
        ("ListManagedClientsResponseDTO", "ManagedClients"),
        ("ListMarketInformationSearchResponseDTO", "MarketInformation"),
        ("ListMarketSearchResponseDTO", "Markets"),
        ("ListOpenPositionsResponseDTO", "OpenPositions"),
        ("ListProductInformationResponseDTO", "ProductInformation"),
        ("ListSpreadMarketsResponseDTO", "Markets"),
        ("ListNewsHeadlinesResponseDTO", "Headlines"),
        ("ListStopLimitOrderHistoryResponseDTO", "StopLimitOrderHistory"),
        ("ListTradeHistoryResponseDTO", "SupplementalOpenOrders"),
        ("ListTradeHistoryResponseDTO", "TradeHistory"),
        ("NewsHeadlinesResponseDTO", "Headlines"),
        ("ManagedClientDTO", "TradingAccounts"),
        ("MarketInformationSearchWithTagsResponseDTO", "Markets"),
        ("MarketInformationSearchWithTagsResponseDTO", "Tags"),
        ("MarketInformationSearchWithoutTagsResponseDTO", "Markets"),
        ("MarketPricesDTO", "MarketState"),
        ("MarketSearchResultDTO", "MarketBreakTimes"),
        ("MarketSearchResultDTO", "MarketEod"),
        ("MarketSearchResultDTO", "MarketPricingTimes"),
        ("NewStopLimitOrderRequestDTO", "IfDone"),
        ("NewTradeOrderRequestDTO", "IfDone"),
        ("PriceAlertResponseDTO", "PriceAlerts"),
        ("SaveClientPreferenceRequestDTO", "ClientPreference"),
        ("SaveMarketInformationRequestDTO", "MarketInformation"),
    }
)


@dataclass(frozen=True)
class EndpointRecord:
    """Endpoint metadata from endpoints.json."""

    name: str
    logical_name: str | None
    version: str | None
    description: str | None
    method: str | None
    target: str | None
    uri_template: str | None
    path: str | None
    content_type: str | None
    envelope: str | None
    parameters: list[JsonObject]
    request_type: str | None
    response_type: str | None
    source_url: str | None
    source_file: str | None
    last_updated: str | None
    raw: JsonObject


@dataclass(frozen=True)
class TypeRecord:
    """Datatype metadata from data-types.json."""

    name: str
    catalog_name: str
    version: str | None
    description: str | None
    properties: list[JsonObject]
    source_url: str | None
    source_file: str | None
    last_updated: str | None
    raw: JsonObject


@dataclass(frozen=True)
class Catalog:
    """Normalized catalog inputs for generator passes."""

    endpoints: list[EndpointRecord]
    datatypes: list[TypeRecord]
    lookups: dict[str, Any]
    unresolved: set[str] = field(default_factory=set)


def load_catalog(root: Path) -> Catalog:
    """Load the StoneX catalog from *root*."""

    endpoints_raw = _load_json_list(root / "endpoints.json")
    datatypes_raw = _load_json_list(root / "data-types.json")
    lookups = _load_json_object(_lookup_path(root))

    endpoints = [_endpoint_record(rec) for rec in endpoints_raw]
    datatypes = [_type_record(rec) for rec in datatypes_raw]
    lookup_names = {python_name(name) for name in lookups}
    known_names = {datatype.name for datatype in datatypes} | lookup_names
    unresolved = _collect_unresolved(datatypes, endpoints, known_names)

    return Catalog(
        endpoints=endpoints,
        datatypes=datatypes,
        lookups=lookups,
        unresolved=unresolved,
    )


def assert_allowed_unresolved(
    catalog: Catalog,
    *,
    allowed: set[str] | frozenset[str] = DEFAULT_ALLOWED_UNRESOLVED,
) -> None:
    """Raise if the catalog has unresolved references outside the *allowed* allowlist.

    Raises:
        ValueError: Listing every unexpected unresolved reference.
    """
    unexpected = sorted(catalog.unresolved - set(allowed))
    if unexpected:
        raise ValueError("unexpected unresolved catalog references: " + ", ".join(unexpected))


def assert_catalog_frozen(
    catalog: Catalog,
    root: Path,
    *,
    version_file: Path = CATALOG_VERSION_FILE,
    git_sha: str | None = None,
) -> None:
    """Raise unless the catalog matches the pinned git SHA and record counts.

    Guards against regenerating from a drifted or dirty catalog checkout.

    Raises:
        ValueError: On a SHA mismatch, a dirty catalog tree, or a record-count mismatch.
    """
    expected_sha, expected_counts = _read_catalog_version(version_file)
    actual_sha = git_sha if git_sha is not None else _catalog_git_sha(root)
    if actual_sha != expected_sha:
        raise ValueError(f"catalog version mismatch: expected {expected_sha}, found {actual_sha}")
    if git_sha is None:
        _assert_catalog_clean(root)

    actual_counts = {
        "endpoints": len(catalog.endpoints),
        "data_types": len(catalog.datatypes),
        "lookups": len(catalog.lookups),
    }
    mismatches = [
        f"{name}=expected {expected_counts[name]} found {actual_counts[name]}"
        for name in ("endpoints", "data_types", "lookups")
        if actual_counts[name] != expected_counts[name]
    ]
    if mismatches:
        raise ValueError("catalog count mismatch: " + ", ".join(mismatches))


def is_enum_record(rec: TypeRecord | Mapping[str, Any]) -> bool:
    """Return whether every property follows a catalog enum shape."""

    properties = _record_properties(rec)
    if not properties:
        return False

    names_are_codes = all(_is_integer_code(prop.get("name")) for prop in properties)
    types_are_codes = all(_is_integer_code(prop.get("type")) for prop in properties)
    return names_are_codes or types_are_codes


def python_type(prop: Mapping[str, Any], known_names: set[str]) -> str:
    """Map a catalog property to the future generated Python annotation name."""

    type_name = _string_or_none(prop.get("type"))
    ref = _string_or_none(prop.get("ref"))
    fmt = _normalize_format(prop.get("format"))

    if not type_name:
        return "Unresolved"

    normalized_type, is_array = _parse_type(type_name)
    inner = _python_type_scalar(normalized_type, ref, fmt, known_names)

    if is_array:
        return f"list[{inner}]"
    return inner


def python_name(name: str) -> str:
    """Return a Python-safe class-style name for a catalog type name."""

    candidate = "".join(_PYTHON_NAME_PART_RE.findall(name))
    if not candidate:
        return "Unresolved"
    if candidate[0].isdigit():
        return f"_{candidate}"
    if keyword.iskeyword(candidate):
        return f"{candidate}_"
    return candidate


def _load_json_list(path: Path) -> list[JsonObject]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} must contain JSON objects")
    return cast(list[JsonObject], data)


def _load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], data)


def _lookup_path(root: Path) -> Path:
    real_name = root / "lookup-codes.json"
    if real_name.exists():
        return real_name
    return root / "lookups.json"


def _endpoint_record(raw: JsonObject) -> EndpointRecord:
    return EndpointRecord(
        name=_required_string(raw, "name"),
        logical_name=_string_or_none(raw.get("logical_name")),
        version=_string_or_none(raw.get("version")),
        description=_string_or_none(raw.get("description")),
        method=_string_or_none(raw.get("method")),
        target=_string_or_none(raw.get("target")),
        uri_template=_string_or_none(raw.get("uri_template")),
        path=_string_or_none(raw.get("path")),
        content_type=_string_or_none(raw.get("content_type")),
        envelope=_string_or_none(raw.get("envelope")),
        parameters=_object_list(raw.get("parameters")),
        request_type=_optional_python_name(raw.get("request_type")),
        response_type=_optional_python_name(raw.get("response_type")),
        source_url=_string_or_none(raw.get("source_url")),
        source_file=_string_or_none(raw.get("source_file")),
        last_updated=_string_or_none(raw.get("last_updated")),
        raw=raw,
    )


def _type_record(raw: JsonObject) -> TypeRecord:
    catalog_name = _required_string(raw, "name")
    properties = _normalized_properties(catalog_name, _object_list(raw.get("properties")))
    return TypeRecord(
        name=python_name(catalog_name),
        catalog_name=catalog_name,
        version=_string_or_none(raw.get("version")),
        description=_string_or_none(raw.get("description")),
        properties=properties,
        source_url=_string_or_none(raw.get("source_url")),
        source_file=_string_or_none(raw.get("source_file")),
        last_updated=_string_or_none(raw.get("last_updated")),
        raw=raw,
    )


def _normalized_properties(catalog_name: str, properties: list[JsonObject]) -> list[JsonObject]:
    owner = python_name(catalog_name)
    normalized: list[JsonObject] = []
    for prop in properties:
        name = _string_or_none(prop.get("name"))
        type_name = _string_or_none(prop.get("type"))
        if (
            name is not None
            and type_name is not None
            and (owner, name) in _ARRAY_PROPERTY_OVERRIDES
            and not _parse_type(type_name)[1]
        ):
            corrected = dict(prop)
            corrected["type"] = f"{type_name} []"
            corrected["required"] = False
            corrected["nullable"] = True
            normalized.append(corrected)
            continue
        normalized.append(prop)
    return normalized


def _collect_unresolved(
    datatypes: list[TypeRecord],
    endpoints: list[EndpointRecord],
    known_names: set[str],
) -> set[str]:
    unresolved: set[str] = set()
    for datatype in datatypes:
        if is_enum_record(datatype):
            continue
        for prop in datatype.properties:
            unresolved.update(_unknown_property_names(prop, known_names, owner=datatype.name))
    for endpoint in endpoints:
        for type_name in (endpoint.request_type, endpoint.response_type):
            if type_name and type_name not in known_names:
                unresolved.add(type_name)
        for param in endpoint.parameters:
            unresolved.update(_unknown_property_names(param, known_names, owner=endpoint.name))
    return unresolved


def _python_type_scalar(
    type_name: str,
    ref: str | None,
    fmt: str | None,
    known_names: set[str],
) -> str:
    if ref:
        known_ref = _known_python_name(ref, known_names)
        return known_ref if known_ref is not None else "Unresolved"
    known_type = _known_python_name(type_name, known_names)
    if known_type is not None:
        return known_type
    if fmt == "wcf-date":
        return "StoneXDateTime"
    if type_name == "integer" or (type_name == "number" and fmt == "long"):
        return "int"
    if type_name in {"decimal", "number"}:
        return "Decimal"
    if type_name == "wcf-date" or (type_name == "string" and fmt == "wcf-date"):
        return "StoneXDateTime"
    if type_name == "boolean":
        return "bool"
    if type_name == "string":
        return "str"
    return "Unresolved"


def _record_properties(rec: TypeRecord | Mapping[str, Any]) -> list[JsonObject]:
    if isinstance(rec, TypeRecord):
        return rec.properties
    return _object_list(rec.get("properties"))


def _required_string(raw: JsonObject, key: str) -> str:
    value = raw.get(key)
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"catalog record is missing required string {key!r}")


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _optional_python_name(value: object) -> str | None:
    name = _string_or_none(value)
    if name is None:
        return None
    return python_name(name)


def _object_list(value: object) -> list[JsonObject]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("catalog field must be a list of objects")
    return cast(list[JsonObject], value)


def _is_integer_code(value: object) -> bool:
    return isinstance(value, str) and value.strip().isdigit() and not value.strip().isidentifier()


def _parse_type(type_name: str) -> tuple[str, bool]:
    is_array = bool(_ARRAY_MARKER_RE.search(type_name))
    without_array = _ARRAY_MARKER_RE.sub(" ", type_name)
    return _normalize_type(without_array), is_array


def _normalize_type(type_name: str) -> str:
    text = " ".join(type_name.strip().split())
    key = text.lower()
    if not key:
        return ""

    alias = _DIRTY_TYPE_ALIASES.get(key)
    if alias is not None:
        return alias

    tokens = key.split()
    first_token_alias = _DIRTY_TYPE_ALIASES.get(tokens[0])
    if first_token_alias in _PRIMITIVE_TYPE_NAMES:
        return first_token_alias
    if len(tokens) > 1:
        first_two_alias = _DIRTY_TYPE_ALIASES.get(" ".join(tokens[:2]))
        if first_two_alias in _PRIMITIVE_TYPE_NAMES:
            return first_two_alias
    return text


def _normalize_format(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.strip().lower()


def _unknown_property_names(
    prop: Mapping[str, Any],
    known_names: set[str],
    *,
    owner: str,
) -> set[str]:
    ref = _string_or_none(prop.get("ref"))
    if ref:
        known_ref = _known_python_name(ref, known_names)
        return set() if known_ref is not None else {python_name(ref)}

    type_name = _string_or_none(prop.get("type"))
    if not type_name:
        prop_name = _string_or_none(prop.get("name"))
        return {f"{owner}.{prop_name}"} if prop_name else set()

    normalized, _ = _parse_type(type_name)
    if (
        _known_python_name(normalized, known_names) is not None
        or normalized in _PRIMITIVE_TYPE_NAMES
    ):
        return set()
    return {python_name(normalized)}


def _known_python_name(type_name: str, known_names: set[str]) -> str | None:
    canonical = python_name(type_name)
    if canonical in known_names or type_name in known_names:
        return canonical
    return None


def _read_catalog_version(version_file: Path) -> tuple[str, dict[str, int]]:
    lines = [
        line.strip()
        for line in version_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) < 2:
        raise ValueError(f"{version_file} must include git SHA and catalog counts")

    counts: dict[str, int] = {}
    for part in lines[1].split():
        key, separator, value = part.partition("=")
        if separator != "=" or key not in {"endpoints", "data_types", "lookups"}:
            continue
        try:
            counts[key] = int(value)
        except ValueError as exc:
            raise ValueError(f"{version_file} has invalid count {part!r}") from exc

    missing = {"endpoints", "data_types", "lookups"} - set(counts)
    if missing:
        raise ValueError(f"{version_file} is missing counts: {', '.join(sorted(missing))}")
    return lines[0], counts


def _catalog_git_sha(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"unable to read catalog git version for {root}") from exc
    return proc.stdout.strip()


def _assert_catalog_clean(root: Path) -> None:
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                ".",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"unable to read catalog git status for {root}") from exc

    dirty = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if dirty:
        raise ValueError("catalog files are dirty: " + ", ".join(dirty))
