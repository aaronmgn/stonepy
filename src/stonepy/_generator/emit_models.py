"""Emit generated model modules from a loaded catalog."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from stonepy._generator.catalog import Catalog, JsonObject, TypeRecord, is_enum_record, python_name
from stonepy._generator.render import (
    BANNER,
    format_python,
    render_docstring,
    render_enum,
    render_enums,
    render_model,
)

__all__ = ["emit_all", "render_enum", "render_model"]

# An id column ends with a capitalized "Id"/"ID" at a camelCase or word boundary (e.g.
# "OrderActionTypeId", "Currency ID") — but not a plain word that merely ends in "id" ("Valid").
_ID_COLUMN_RE = re.compile(r"(?:[a-z]|\s|^)(?:Id|ID)$")

# Request models whose fields the catalog marks required, but the endpoint documents as a choice of
# filters (supply exactly one). Forcing them optional makes the request constructible. Keyed by
# model name -> the wire field names to default to None.
_FORCE_OPTIONAL_FIELDS: dict[str, set[str]] = {
    "ListNewsHeadlinesRequestDTO": {
        "Source",
        "Category",
        "MarketId",
        "MarketName",
        "RicCode",
        "MaxResults",
        "CultureId",
    },
}


def emit_all(catalog: Catalog, out_dir: Path) -> None:
    """Write generated model modules under *out_dir*/models."""

    models_dir = out_dir / "models"
    if models_dir.exists():
        shutil.rmtree(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    lookup_records = _lookup_enum_records(catalog.lookups)
    known_names = {rec.name for rec in catalog.datatypes} | {rec.name for rec in lookup_records}
    enum_records = [rec for rec in catalog.datatypes if is_enum_record(rec)] + lookup_records
    enum_names = {rec.name for rec in enum_records}
    request_types = _request_type_names(catalog, known_names)
    cyclic_fields = _cyclic_ref_fields(catalog.datatypes)

    for rec in catalog.datatypes:
        if is_enum_record(rec):
            continue
        force_optional = cyclic_fields.get(rec.name, set()) | _FORCE_OPTIONAL_FIELDS.get(
            rec.name, set()
        )
        (models_dir / f"{rec.name}.py").write_text(
            render_model(
                rec,
                known_names,
                request_types=request_types,
                enum_names=enum_names,
                force_optional=force_optional or None,
            ),
            encoding="utf-8",
        )

    (models_dir / "enums.py").write_text(render_enums(enum_records), encoding="utf-8")
    (models_dir / "__init__.py").write_text(
        _render_init(_non_enum_records(catalog.datatypes), enum_records),
        encoding="utf-8",
    )


def _cyclic_ref_fields(records: list[TypeRecord]) -> dict[str, set[str]]:
    """Map each model to the catalog names of its model-ref fields that form a reference cycle.

    A required field whose referenced type can transitively reach back to the owning model has no
    finite validating JSON payload (e.g. ``ApiOrderResponseDTO.OCO`` references itself). The
    catalog does not mark such refs ``required false``, so they are emitted required-by-default and
    make the endpoint's response unparseable. Forcing the cycle-closing fields optional breaks the
    recursion while leaving acyclic required refs untouched.
    """

    names = {rec.name for rec in records}
    edges: dict[str, list[tuple[str, str]]] = {}
    for rec in records:
        refs: list[tuple[str, str]] = []
        for prop in rec.properties:
            field = prop.get("name")
            ref = prop.get("ref")
            if isinstance(field, str) and isinstance(ref, str) and ref in names:
                refs.append((field, ref))
        edges[rec.name] = refs

    def reaches(start: str, target: str, seen: set[str]) -> bool:
        for _, ref in edges.get(start, []):
            if ref == target:
                return True
            if ref not in seen:
                seen.add(ref)
                if reaches(ref, target, seen):
                    return True
        return False

    cyclic: dict[str, set[str]] = {}
    for model, refs in edges.items():
        for field, ref in refs:
            if ref == model or reaches(ref, model, set()):
                cyclic.setdefault(model, set()).add(field)
    return cyclic


def _non_enum_records(records: list[TypeRecord]) -> list[TypeRecord]:
    return [rec for rec in records if not is_enum_record(rec)]


def _render_init(model_records: list[TypeRecord], enum_records: list[TypeRecord]) -> str:
    lines = [
        BANNER,
        render_docstring(
            "Generated Pydantic models and IntEnum types for the StoneX CIAPI v2 API. "
            "Every request and response DTO is importable from this package.",
            indent=0,
        ),
        "from __future__ import annotations\n\n",
    ]

    for rec in sorted(model_records, key=lambda item: item.name):
        lines.append(f"from .{rec.name} import {rec.name}\n")
    for rec in sorted(enum_records, key=lambda item: item.name):
        lines.append(f"from .enums import {rec.name}\n")

    exported = sorted([rec.name for rec in model_records] + [rec.name for rec in enum_records])
    lines.append("\n__all__ = [\n")
    for name in exported:
        lines.append(f'    "{name}",\n')
    lines.append("]\n")

    if model_records:
        lines.append("\nfor _model in (\n")
        for rec in sorted(model_records, key=lambda item: item.name):
            lines.append(f"    {rec.name},\n")
        lines.append("):\n")
        lines.append("    _model.model_rebuild(_types_namespace=globals(), raise_errors=False)\n")
        lines.append("del _model\n")
    return format_python("".join(lines))


def _request_type_names(catalog: Catalog, known_names: set[str]) -> set[str]:
    request_types = {
        endpoint.request_type for endpoint in catalog.endpoints if endpoint.request_type
    }
    for endpoint in catalog.endpoints:
        for param in endpoint.parameters:
            location = param.get("in") or param.get("location")
            if location not in {"body", "query"}:
                continue
            for key in ("ref", "type"):
                raw_name = param.get(key)
                if isinstance(raw_name, str) and python_name(raw_name) in known_names:
                    request_types.add(python_name(raw_name))
    return {name for name in request_types if name is not None}


def _lookup_enum_records(lookups: dict[str, object]) -> list[TypeRecord]:
    records: list[TypeRecord] = []
    for lookup_name, raw_table in sorted(lookups.items()):
        if not isinstance(raw_table, dict):
            continue
        rows = raw_table.get("rows")
        if not isinstance(rows, list):
            continue
        properties = _lookup_properties(rows)
        if not properties:
            continue
        records.append(
            TypeRecord(
                name=python_name(lookup_name),
                catalog_name=lookup_name,
                version=None,
                description=None,
                properties=properties,
                source_url=None,
                source_file=None,
                last_updated=None,
                raw={"name": lookup_name, "properties": properties},
            )
        )
    return records


def _lookup_properties(rows: list[object]) -> list[JsonObject]:
    properties: list[JsonObject] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code_key = _lookup_code_key(row)
        label_key = _lookup_label_key(row, code_key)
        if code_key is None or label_key is None:
            continue
        code = row.get(code_key)
        label = row.get(label_key)
        if not isinstance(code, str) or not code.strip().isdigit() or not isinstance(label, str):
            continue
        properties.append({"name": label, "type": code, "format": None, "ref": None})
    return properties


def _lookup_code_key(row: dict[object, object]) -> str | None:
    keys = [key for key in row if isinstance(key, str)]
    for key in keys:
        if "code" in key.lower():
            return key
    # Fall back to an id column (e.g. "OrderActionTypeId", "Currency ID") when the table has
    # no explicit "<Thing> Code" column. Require a real "Id"/"ID" suffix at a word/camelCase
    # boundary so plain words ending in "id" (e.g. "Valid") do not false-match. Non-numeric picks
    # are rejected downstream.
    for key in keys:
        if _ID_COLUMN_RE.search(key.strip()):
            return key
    return None


def _lookup_label_key(row: dict[object, object], code_key: str | None) -> str | None:
    if "Description" in row:
        return "Description"
    for key in row:
        if isinstance(key, str) and key != code_key:
            return key
    return None
