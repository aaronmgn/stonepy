"""Emit generated contract tests for generated models and endpoints."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from stonepy._generator.catalog import (
    Catalog,
    EndpointRecord,
    TypeRecord,
    is_enum_record,
    python_name,
    python_type,
)
from stonepy._generator.emit_endpoints import _is_idempotent as _endpoint_is_idempotent
from stonepy._generator.emit_endpoints import _params as _endpoint_params
from stonepy._generator.emit_endpoints import endpoint_spec_name, resolved_path, target_module
from stonepy._generator.emit_models import _cyclic_ref_fields, _lookup_enum_records
from stonepy._generator.render import BANNER, field_name, format_python

__all__ = ["emit_contract_tests"]

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def emit_contract_tests(catalog: Catalog, out_dir: Path) -> None:
    """Write generated contract tests under *out_dir*/tests/contract."""

    contract_dir = out_dir / "tests" / "contract"
    if contract_dir.exists():
        shutil.rmtree(contract_dir)
    contract_dir.mkdir(parents=True, exist_ok=True)

    (contract_dir / "test_models_roundtrip.py").write_text(
        _render_models_roundtrip(catalog),
        encoding="utf-8",
    )
    (contract_dir / "test_endpoint_specs.py").write_text(
        _render_endpoint_specs(catalog),
        encoding="utf-8",
    )
    (contract_dir / "test_lookup_enums.py").write_text(
        _render_lookup_enums(catalog),
        encoding="utf-8",
    )
    (contract_dir / "test_datatype_enums.py").write_text(
        _render_datatype_enums(catalog),
        encoding="utf-8",
    )


def _render_models_roundtrip(catalog: Catalog) -> str:
    model_records = sorted(
        [rec for rec in catalog.datatypes if not is_enum_record(rec)],
        key=lambda rec: rec.name,
    )
    model_records_by_name = {rec.name: rec for rec in model_records}
    lookup_records = _lookup_enum_records(catalog.lookups)
    known_names = {rec.name for rec in catalog.datatypes} | {rec.name for rec in lookup_records}
    enum_samples = _enum_samples(catalog.datatypes + lookup_records)
    cyclic_fields = _cyclic_ref_fields(catalog.datatypes)
    cases = [
        _model_case(
            rec,
            known_names=known_names,
            model_records_by_name=model_records_by_name,
            enum_samples=enum_samples,
            cyclic_fields=cyclic_fields,
        )
        for rec in model_records
    ]
    has_constructs = any(case.construct for case in cases)

    lines = [
        BANNER,
        "from __future__ import annotations\n\n",
        "from datetime import UTC, datetime\n",
        "from decimal import Decimal\n\n",
    ]
    if has_constructs:
        lines.append("from typing import Any, cast\n\n")
    lines.append("import pytest\n")
    if model_records:
        lines.append("from stonepy._core.models import StoneXModel\n")
        lines.append(f"from stonepy.models import {', '.join(rec.name for rec in model_records)}\n")
    lines.append("\n")

    lines.append("MODEL_CASES = [\n")
    for case in cases:
        args = [
            case.model_name,
            _dict_literal(case.payload),
        ]
        if has_constructs:
            args.append(str(case.construct))
        lines.append(f"    pytest.param({', '.join(args)}, id={json.dumps(case.model_name)}),\n")
    lines.append("]\n\n\n")

    if cases:
        if has_constructs:
            lines.extend(
                [
                    '@pytest.mark.parametrize("model_cls, payload, construct", MODEL_CASES)\n',
                    "def test_generated_model_roundtrip(\n",
                    "    model_cls: type[StoneXModel],\n",
                    "    payload: dict[str, object],\n",
                    "    construct: bool,\n",
                    ") -> None:\n",
                    "    if construct:\n",
                    (
                        "        # required recursive model graph has no finite validating "
                        "JSON payload\n"
                    ),
                    "        model = model_cls.model_construct(**cast(dict[str, Any], payload))\n",
                    "        dumped = model.model_dump(by_alias=True, exclude_unset=True)\n",
                    "        round_tripped = model_cls.model_construct(**model.__dict__)\n",
                    "        assert round_tripped.model_dump(\n",
                    "            by_alias=True, exclude_unset=True\n",
                    "        ) == dumped\n",
                    "        return\n",
                ]
            )
        else:
            lines.extend(
                [
                    '@pytest.mark.parametrize("model_cls, payload", MODEL_CASES)\n',
                    "def test_generated_model_roundtrip(\n",
                    "    model_cls: type[StoneXModel],\n",
                    "    payload: dict[str, object],\n",
                    ") -> None:\n",
                ]
            )
        lines.extend(
            [
                "    model = model_cls(**payload)\n",
                "    dumped = model.model_dump(by_alias=True)\n",
                "    round_tripped = model_cls.model_validate(dumped)\n",
                "    assert round_tripped.model_dump(by_alias=True) == dumped\n",
            ]
        )
    else:
        lines.extend(
            [
                "def test_no_generated_models() -> None:\n",
                '    pytest.skip("catalog contains no generated models")\n',
            ]
        )
    return format_python("".join(lines))


def _render_endpoint_specs(catalog: Catalog) -> str:
    endpoint_cases = sorted(
        [
            _EndpointCase(
                module_name=target_module(rec.target),
                spec_name=endpoint_spec_name(rec),
                method=(rec.method or "GET").upper(),
                path=resolved_path(rec),
                endpoint_name=rec.name,
                has_declared_response=rec.response_type is not None,
                idempotent=_endpoint_is_idempotent(rec, (rec.method or "GET").upper()),
                auth_policy=_auth_policy(rec),
                rate_limit_bucket=target_module(rec.target),
                request_model=_request_model_name(rec, catalog),
                params=_param_fields(rec),
            )
            for rec in catalog.endpoints
        ],
        key=lambda case: (case.module_name, case.spec_name, case.endpoint_name),
    )
    lines = [
        BANNER,
        "from __future__ import annotations\n\n",
        "from importlib import import_module\n\n",
        "import pytest\n",
    ]
    if endpoint_cases:
        lines.append("from stonepy._core.endpoint import EndpointSpec\n")
        lines.append("from stonepy._core.models import ResponseModel\n")
    for module_name in sorted({case.module_name for case in endpoint_cases}):
        alias = _endpoint_module_alias(module_name)
        lines.append(f'{alias} = import_module("stonepy._endpoints.{module_name}")\n')
    lines.append("\n")

    lines.append("ENDPOINT_CASES = [\n")
    for case in endpoint_cases:
        lines.append(
            "    pytest.param("
            f"{_endpoint_module_alias(case.module_name)}.{case.spec_name}, "
            f"{json.dumps(case.method)}, "
            f"{json.dumps(case.path)}, "
            f"{case.has_declared_response}, "
            f"{case.idempotent}, "
            f"{json.dumps(case.auth_policy)}, "
            f"{json.dumps(case.rate_limit_bucket)}, "
            f"{_string_or_none_literal(case.request_model)}, "
            f"{_params_literal(case.params)}, "
            f"id={json.dumps(case.endpoint_name)}"
            "),\n"
        )
    lines.append("]\n\n\n")

    if endpoint_cases:
        lines.extend(
            [
                "@pytest.mark.parametrize(\n",
                '    "spec, method, path, has_declared_response, idempotent, auth_policy, "\n',
                '    "rate_limit_bucket, request_model, params",\n',
                "    ENDPOINT_CASES,\n",
                ")\n",
                "def test_generated_endpoint_spec_matches_catalog(\n",
                "    spec: EndpointSpec[ResponseModel],\n",
                "    method: str,\n",
                "    path: str,\n",
                "    has_declared_response: bool,\n",
                "    idempotent: bool,\n",
                "    auth_policy: str,\n",
                "    rate_limit_bucket: str,\n",
                "    request_model: str | None,\n",
                "    params: tuple[tuple[str, str, str], ...],\n",
                ") -> None:\n",
                "    assert spec.method == method\n",
                "    assert spec.path == path\n",
                "    assert spec.idempotent is idempotent\n",
                "    assert spec.auth_policy.name == auth_policy\n",
                "    assert spec.rate_limit_bucket == rate_limit_bucket\n",
                "    if request_model is None:\n",
                "        assert spec.request_model is None\n",
                "    else:\n",
                "        assert spec.request_model is not None\n",
                "        assert spec.request_model.__name__ == request_model\n",
                "    param_fields = tuple(\n",
                "        (param.name, param.location, param.python_name)\n",
                "        for param in spec.params\n",
                "    )\n",
                "    assert param_fields == params\n",
                "    if has_declared_response:\n",
                "        assert spec.response_model is not ResponseModel\n",
            ]
        )
    else:
        lines.extend(
            [
                "def test_no_generated_endpoints() -> None:\n",
                '    pytest.skip("catalog contains no generated endpoints")\n',
            ]
        )
    return format_python("".join(lines))


def _render_lookup_enums(catalog: Catalog) -> str:
    return _render_enum_value_test(
        _lookup_enum_records(catalog.lookups),
        cases_var="LOOKUP_ENUM_CASES",
        test_name="test_generated_lookup_enum_matches_catalog",
        no_enums_func="test_no_generated_lookup_enums",
        no_enums_msg="catalog contains no generated lookup enums",
    )


def _render_datatype_enums(catalog: Catalog) -> str:
    return _render_enum_value_test(
        [rec for rec in catalog.datatypes if is_enum_record(rec)],
        cases_var="DATATYPE_ENUM_CASES",
        test_name="test_generated_datatype_enum_matches_catalog",
        no_enums_func="test_no_generated_datatype_enums",
        no_enums_msg="catalog contains no enum-shaped datatypes",
    )


def _render_enum_value_test(
    records: list[TypeRecord],
    *,
    cases_var: str,
    test_name: str,
    no_enums_func: str,
    no_enums_msg: str,
) -> str:
    lines = [BANNER, "from __future__ import annotations\n\n"]
    if records:
        lines.extend(
            [
                "from enum import IntEnum\n\n",
                "import pytest\n",
                f"from stonepy.models import {', '.join(rec.name for rec in records)}\n",
                "\n",
                f"{cases_var} = [\n",
            ]
        )
        for rec in records:
            lines.append(
                "    pytest.param("
                f"{rec.name}, "
                f"{_int_dict_literal(_enum_member_map(rec))}, "
                f"id={json.dumps(rec.catalog_name or rec.name)}"
                "),\n"
            )
        lines.extend(
            [
                "]\n\n\n",
                f'@pytest.mark.parametrize("enum_cls, members", {cases_var})\n',
                f"def {test_name}(\n",
                "    enum_cls: type[IntEnum], members: dict[str, int]\n",
                ") -> None:\n",
                "    assert {\n",
                "        name: member.value for name, member in enum_cls.__members__.items()\n",
                "    } == members\n",
            ]
        )
    else:
        lines.extend(
            [
                "import pytest\n\n",
                f"def {no_enums_func}() -> None:\n",
                f'    pytest.skip("{no_enums_msg}")\n',
            ]
        )
    return format_python("".join(lines))


class _ModelCase:
    def __init__(
        self,
        *,
        model_name: str,
        payload: dict[str, str],
        construct: bool,
    ) -> None:
        self.model_name = model_name
        self.payload = payload
        self.construct = construct


class _EndpointCase:
    def __init__(
        self,
        *,
        module_name: str,
        spec_name: str,
        method: str,
        path: str,
        endpoint_name: str,
        has_declared_response: bool,
        idempotent: bool,
        auth_policy: str,
        rate_limit_bucket: str,
        request_model: str | None,
        params: tuple[tuple[str, str, str], ...],
    ) -> None:
        self.module_name = module_name
        self.spec_name = spec_name
        self.method = method
        self.path = path
        self.endpoint_name = endpoint_name
        self.has_declared_response = has_declared_response
        self.idempotent = idempotent
        self.auth_policy = auth_policy
        self.rate_limit_bucket = rate_limit_bucket
        self.request_model = request_model
        self.params = params


def _model_case(
    rec: TypeRecord,
    *,
    known_names: set[str],
    model_records_by_name: Mapping[str, TypeRecord],
    enum_samples: Mapping[str, int],
    cyclic_fields: Mapping[str, set[str]],
) -> _ModelCase:
    try:
        payload = _model_payload(
            rec,
            known_names=known_names,
            model_records_by_name=model_records_by_name,
            enum_samples=enum_samples,
            cyclic_fields=cyclic_fields,
            stack=(rec.name,),
        )
    except _RecursiveModelPayload:
        payload = _construct_payload(
            rec,
            known_names=known_names,
            model_records_by_name=model_records_by_name,
            enum_samples=enum_samples,
            cyclic_fields=cyclic_fields,
        )
        return _ModelCase(
            model_name=rec.name,
            payload=payload,
            construct=True,
        )
    return _ModelCase(model_name=rec.name, payload=payload, construct=False)


def _model_payload(
    rec: TypeRecord,
    *,
    known_names: set[str],
    model_records_by_name: Mapping[str, TypeRecord],
    enum_samples: Mapping[str, int],
    cyclic_fields: Mapping[str, set[str]],
    stack: tuple[str, ...],
) -> dict[str, str]:
    optional_here = cyclic_fields.get(rec.name, set())
    payload: dict[str, str] = {}
    for prop in rec.properties:
        raw_name = prop.get("name")
        if not isinstance(raw_name, str) or field_name(raw_name) is None:
            continue
        # Cycle-closing model refs are emitted optional (see emit_models._cyclic_ref_fields), so
        # skip them here exactly as catalog-optional props are skipped.
        if _is_optional_property(prop) or raw_name in optional_here:
            continue

        annotation = python_type(prop, known_names)
        sample = _sample_value(
            annotation,
            enum_samples=enum_samples,
            model_records_by_name=model_records_by_name,
            known_names=known_names,
            cyclic_fields=cyclic_fields,
            stack=stack,
        )
        payload[raw_name] = sample

    return payload


def _construct_payload(
    rec: TypeRecord,
    *,
    known_names: set[str],
    model_records_by_name: Mapping[str, TypeRecord],
    enum_samples: Mapping[str, int],
    cyclic_fields: Mapping[str, set[str]],
) -> dict[str, str]:
    optional_here = cyclic_fields.get(rec.name, set())
    payload: dict[str, str] = {}
    for prop in rec.properties:
        raw_name = prop.get("name")
        if not isinstance(raw_name, str):
            continue
        name = field_name(raw_name)
        if name is None or _is_optional_property(prop) or raw_name in optional_here:
            continue

        annotation = python_type(prop, known_names)
        payload[name] = _construct_sample_value(
            annotation,
            enum_samples=enum_samples,
            model_records_by_name=model_records_by_name,
            known_names=known_names,
            cyclic_fields=cyclic_fields,
        )
    return payload


def _construct_sample_value(
    annotation: str,
    *,
    enum_samples: Mapping[str, int],
    model_records_by_name: Mapping[str, TypeRecord],
    known_names: set[str],
    cyclic_fields: Mapping[str, set[str]],
) -> str:
    if annotation.startswith("list["):
        return "[]"
    if annotation in model_records_by_name:
        return f"{annotation}.model_construct()"
    return _sample_value(
        annotation,
        enum_samples=enum_samples,
        model_records_by_name=model_records_by_name,
        known_names=known_names,
        cyclic_fields=cyclic_fields,
        stack=(),
    )


def _sample_value(
    annotation: str,
    *,
    enum_samples: Mapping[str, int],
    model_records_by_name: Mapping[str, TypeRecord],
    known_names: set[str],
    cyclic_fields: Mapping[str, set[str]],
    stack: tuple[str, ...],
) -> str:
    if annotation.startswith("list["):
        return "[]"
    if annotation in enum_samples:
        return str(enum_samples[annotation])
    if annotation == "int":
        return "1"
    if annotation == "Decimal":
        return 'Decimal("1.23")'
    if annotation == "str":
        return '"x"'
    if annotation == "bool":
        return "False"
    if annotation == "StoneXDateTime":
        return "datetime(2020, 1, 1, tzinfo=UTC)"
    if annotation == "Unresolved":
        return "None"
    if annotation in model_records_by_name:
        if annotation in stack:
            raise _RecursiveModelPayload(model_name=annotation, stack=stack)
        return _dict_literal(
            _model_payload(
                model_records_by_name[annotation],
                known_names=known_names,
                model_records_by_name=model_records_by_name,
                enum_samples=enum_samples,
                cyclic_fields=cyclic_fields,
                stack=(*stack, annotation),
            )
        )
    if annotation in known_names:
        return "None"
    return "None"


class _RecursiveModelPayload(Exception):
    def __init__(self, *, model_name: str, stack: tuple[str, ...]) -> None:
        self.model_name = model_name
        self.stack = stack
        super().__init__(model_name)


def _enum_samples(records: list[TypeRecord]) -> dict[str, int]:
    samples: dict[str, int] = {}
    for rec in records:
        if not is_enum_record(rec):
            continue
        values = [_enum_value(prop) for prop in rec.properties]
        samples[rec.name] = next(value for value in values if value is not None)
    return samples


def _enum_value(prop: Mapping[str, Any]) -> int | None:
    for key in ("type", "name"):
        value = prop.get(key)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None


def _enum_member_map(rec: TypeRecord) -> dict[str, int]:
    members: dict[str, int] = {}
    used_names: set[str] = set()
    for prop in rec.properties:
        raw_name = prop.get("name")
        raw_type = prop.get("type")
        label: str | None = None
        code: int | None = None
        if isinstance(raw_type, str) and raw_type.strip().isdigit() and isinstance(raw_name, str):
            label = raw_name
            code = int(raw_type.strip())
        elif isinstance(raw_name, str) and raw_name.strip().isdigit() and isinstance(raw_type, str):
            label = raw_type
            code = int(raw_name.strip())
        if label is None or code is None:
            continue
        member_name = _unique_member_name(python_name(label), used_names)
        members[member_name] = code
    return members


def _unique_member_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        used_names.add(name)
        return name

    suffix = 2
    while f"{name}_{suffix}" in used_names:
        suffix += 1
    unique = f"{name}_{suffix}"
    used_names.add(unique)
    return unique


def _is_optional_property(prop: Mapping[str, Any]) -> bool:
    raw_type = prop.get("type")
    if not isinstance(raw_type, str) or not raw_type:
        return True

    normalized = " ".join(raw_type.lower().split())
    return "nullable true" in normalized or "required false" in normalized


def _dict_literal(items: Mapping[str, str]) -> str:
    if not items:
        return "{}"
    pairs = [f"{json.dumps(key)}: {value}" for key, value in sorted(items.items())]
    return "{" + ", ".join(pairs) + "}"


def _int_dict_literal(items: Mapping[str, int]) -> str:
    if not items:
        return "{}"
    pairs = [f"{json.dumps(key)}: {value}" for key, value in sorted(items.items())]
    return "{" + ", ".join(pairs) + "}"


def _string_or_none_literal(value: str | None) -> str:
    return "None" if value is None else json.dumps(value)


def _params_literal(params: tuple[tuple[str, str, str], ...]) -> str:
    if not params:
        return "()"
    items = [
        f"({json.dumps(name)}, {json.dumps(location)}, {json.dumps(python_name)})"
        for name, location, python_name in params
    ]
    return "(" + ", ".join(items) + ",)"


def _endpoint_module_alias(module_name: str) -> str:
    return f"_ep_{module_name}"


def _auth_policy(rec: EndpointRecord) -> str:
    raw_names = [rec.name, rec.logical_name or ""]
    normalized_names = {"".join(ch for ch in name.lower() if ch.isalnum()) for name in raw_names}
    if "logon" in normalized_names or (rec.path or "").lower() == "/session/v2/session":
        return "NONE"
    return "SESSION"


def _request_model_name(rec: EndpointRecord, catalog: Catalog) -> str | None:
    if rec.request_type is not None:
        return rec.request_type
    known_names = {datatype.name for datatype in catalog.datatypes}
    candidates: list[str] = []
    for param in rec.parameters:
        location = param.get("in") or param.get("location")
        if location not in {"body", "query"}:
            continue
        for key in ("ref", "type"):
            value = param.get(key)
            candidate = python_name(value) if isinstance(value, str) else None
            if candidate is not None and candidate in known_names and candidate not in candidates:
                candidates.append(candidate)
    return candidates[0] if len(candidates) == 1 else None


def _param_fields(rec: EndpointRecord) -> tuple[tuple[str, str, str], ...]:
    # Reuse the endpoint generator's parameter resolution so the contract expectation always
    # matches the emitted ``EndpointSpec.params`` (including params synthesized from URI
    # templates the catalog's parameter list omits).
    params = _endpoint_params(rec.parameters, None, path=resolved_path(rec))
    return tuple((param.name, param.location, param.python_name) for param in params)
