"""Emit generated endpoint binding modules from a loaded catalog."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

from stonepy._generator.catalog import Catalog, EndpointRecord, python_name, python_type
from stonepy._generator.render import BANNER, field_name, format_python, render_docstring

__all__ = [
    "emit_all",
    "endpoint_spec_name",
    "is_host_rooted",
    "render_binding",
    "resolved_path",
    "target_module",
]

_VERSION_SUFFIX_RE = re.compile(r"\s+v\d+\s*$", re.IGNORECASE)
_DEFAULT_VALUE_RE = re.compile(r"\bdefault\s+([^\s,;]+)", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
# Some catalog descriptions trail off with this dangling cross-reference to a removed HTTP
# service page; drop it so the generated docstring reads cleanly.
_HTTP_SERVICE_FRAGMENT_RE = re.compile(
    r"\s*For a more comprehensive order response,\s+see the HTTP service\s+\."
)
_TARGET_ALIASES = {
    "pricealert": "price_alert",
    "useraccount": "user_account",
    "watchlist": "watchlist",
    "watchlists": "watchlist",
}
_IDEMPOTENT_METHODS = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"}
_RETRY_SAFE_ENDPOINT_OVERRIDES: set[tuple[str, str]] = {
    ("clientpreference", "Get"),
    ("clientpreference", "GetList"),
    ("clientpreference", "GetOverriddenSettings"),
    ("market", "ListMarketInformation"),
    ("message", "GetClientApplicationMessageTranslationWithInterestingItems"),
    ("order", "ListActiveOrders"),
}

# Catalog gap: these endpoints document "leave the market name and code parameters empty to
# return all markets", but the catalog leaves those filters bare-typed (no required/nullable/
# default marker), so they would emit as required positionals and the documented "return all"
# call would be unreachable. A bare type carries no signal to tell an optional filter from a
# genuinely-required key (e.g. GetStory.storyID), so optionality cannot be inferred — this
# curated map (keyed by (target_module, endpoint name)) forces exactly the documented filters
# optional. Mirrors the catalog's DEFAULT_ALLOWED_UNRESOLVED allowlist for declared gaps.
_OPTIONAL_PARAM_OVERRIDES: dict[tuple[str, str], frozenset[str]] = {
    ("spread", "ListSpreadMarkets"): frozenset({"searchByMarketName", "searchByMarketCode"}),
    ("cfd", "ListCfdMarkets"): frozenset({"marketName", "marketCode"}),
}

# Catalog gap: the upstream "GetActiveStopLimitOrder v2" doc page templates its URI as
# "/v2{orderId}/activeStopLimitOrder" — missing the slash after "v2" that every sibling v2 order
# endpoint carries (GetOpenPosition v2 = "/v2/{orderId}/openPosition", GetOrder v2 =
# "/v2/order/{orderId}"). Verified against docs.labs.gaincapital.com as an upstream documentation
# typo (the page's own example request is ".../order/123456/activeStopLimitOrder"), so without this
# correction the generated client would request the non-existent "/order/v2{orderId}/..." path.
# Keyed by (target_module, endpoint name); mirrors the other curated catalog-gap overrides.
_PATH_OVERRIDES: dict[tuple[str, str], str] = {
    (
        "order",
        "GetActiveStopLimitOrder v2",
    ): "/order/v2/{orderId}/activeStopLimitOrder?clientAccountId={clientAccountId}",
    # CIAPI serves logon and account lookup from the host root ("https://host/v2/...", see
    # _HOST_ROOTED_ENDPOINTS), not the catalog's best-effort "/{target}/v2/..." which doubles the
    # target segment and 401s. Confirmed against the reference pygcapi client (BASE_URL_V2 =
    # "https://host/v2"): logon at "/v2/session", account at "/v2/UserAccount/...".
    ("session", "LogOn v2"): "/v2/session",
    ("user_account", "GetClientAndTradingAccount v2"): "/v2/UserAccount/ClientAndTradingAccount",
    # CIAPI never shipped a working v2 margin route; account margin is served by the v1 endpoint
    # "/margin/ClientAccountMargin" under the /TradingAPI base (the catalog's doubled
    # "/margin/v2/margin/..." path 404s). Stays base-rooted, so no _HOST_ROOTED_ENDPOINTS entry.
    ("margin", "GetClientAccountMargin v2"): "/margin/ClientAccountMargin",
}

# CIAPI serves a few v2 endpoints from the host root ("https://host/v2/...") rather than under the
# configured "/TradingAPI" base; their path is resolved against the host root (see
# transport.build_request). Keyed by (target_module, endpoint name).
_HOST_ROOTED_ENDPOINTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("session", "LogOn v2"),
        ("user_account", "GetClientAndTradingAccount v2"),
    }
)


def endpoint_summary(rec: EndpointRecord) -> str:
    """Return a one-paragraph summary of an endpoint for use as a wrapper docstring."""

    if rec.description:
        text = _HTTP_SERVICE_FRAGMENT_RE.sub("", rec.description.strip()).strip()
        if text:
            return text
    return f"Call the StoneX {rec.name} endpoint."


def resolved_path(rec: EndpointRecord) -> str:
    """Return the endpoint path, applying curated catalog path-typo corrections.

    The catalog's ``path``/``uri_template`` is authoritative except for the declared upstream
    doc typos in ``_PATH_OVERRIDES``; this single resolver keeps the generated endpoint spec and
    the generated contract test in agreement on the corrected value.
    """

    return _PATH_OVERRIDES.get(
        (target_module(rec.target), rec.name), rec.path or rec.uri_template or ""
    )


def is_host_rooted(rec: EndpointRecord) -> bool:
    """Return whether *rec* is served from the host root rather than the configured base URL."""

    return (target_module(rec.target), rec.name) in _HOST_ROOTED_ENDPOINTS


def target_module(name: str | None) -> str:
    """Return the generated endpoint module name for a catalog target."""

    if not name:
        return "misc"

    compact = re.sub(r"[^0-9A-Za-z]+", "", name).lower()
    if compact in _TARGET_ALIASES:
        return _TARGET_ALIASES[compact]

    normalized = field_name(name)
    return normalized or "misc"


def endpoint_spec_name(rec: EndpointRecord) -> str:
    """Return the generated EndpointSpec symbol name for a catalog endpoint."""

    return f"{_function_name(rec).upper()}_SPEC"


def render_binding(
    rec: EndpointRecord,
    *,
    known_model_names: Collection[str] | None = None,
    include_imports: bool = True,
) -> str:
    """Render one endpoint spec and its sync/async wrappers."""

    binding = _binding(rec, known_model_names=known_model_names)
    lines: list[str] = []
    if include_imports:
        lines.extend(_module_header([binding]))
    lines.extend(_binding_lines(binding))
    source = "".join(lines)
    return _annotate_unwrappable_long_lines(format_python(source)) if include_imports else source


def emit_all(catalog: Catalog, out_dir: Path) -> None:
    """Write generated endpoint modules under *out_dir*/_endpoints."""

    endpoints_dir = out_dir / "_endpoints"
    if endpoints_dir.exists():
        shutil.rmtree(endpoints_dir)
    endpoints_dir.mkdir(parents=True, exist_ok=True)

    known_model_names = {rec.name for rec in catalog.datatypes}
    grouped: dict[str, list[_Binding]] = {}
    for rec in catalog.endpoints:
        grouped.setdefault(target_module(rec.target), []).append(
            _binding(rec, known_model_names=known_model_names)
        )

    for module_name, bindings in sorted(grouped.items()):
        (endpoints_dir / f"{module_name}.py").write_text(
            _render_module(bindings),
            encoding="utf-8",
        )

    (endpoints_dir / "__init__.py").write_text(
        _render_init(grouped),
        encoding="utf-8",
    )


class _Param:
    def __init__(
        self,
        *,
        name: str,
        location: str,
        python_name: str,
        annotation: str,
        optional: bool = False,
        default_expr: str | None = None,
    ) -> None:
        self.name = name
        self.location = location
        self.python_name = python_name
        self.annotation = annotation
        self.optional = optional
        self.default_expr = default_expr


class _Binding:
    def __init__(
        self,
        *,
        rec: EndpointRecord,
        function_name: str,
        async_function_name: str,
        spec_name: str,
        method: str,
        path: str,
        host_rooted: bool,
        rate_limit_bucket: str,
        auth_policy: str,
        idempotent: bool,
        params: list[_Param],
        request_model: str | None,
        response_model: str,
        request_annotation: str | None,
        response_annotation: str,
        unresolved_response_model: str | None,
        uses_mapping: bool,
        model_imports: set[str],
        core_model_imports: set[str],
    ) -> None:
        self.rec = rec
        self.function_name = function_name
        self.async_function_name = async_function_name
        self.spec_name = spec_name
        self.method = method
        self.path = path
        self.host_rooted = host_rooted
        self.rate_limit_bucket = rate_limit_bucket
        self.auth_policy = auth_policy
        self.idempotent = idempotent
        self.params = params
        self.request_model = request_model
        self.response_model = response_model
        self.request_annotation = request_annotation
        self.response_annotation = response_annotation
        self.unresolved_response_model = unresolved_response_model
        self.uses_mapping = uses_mapping
        self.model_imports = model_imports
        self.core_model_imports = core_model_imports


def _binding(
    rec: EndpointRecord,
    *,
    known_model_names: Collection[str] | None,
) -> _Binding:
    function_name = _function_name(rec)
    known_models = set(known_model_names) if known_model_names is not None else None
    request_model = _known_type(rec.request_type, known_models)
    response_model = _response_model_type(rec.response_type, known_models)
    unresolved_response_model = _unresolved_response_model(rec.response_type, known_models)
    optional_overrides = _OPTIONAL_PARAM_OVERRIDES.get(
        (target_module(rec.target), rec.name), frozenset()
    )
    path = resolved_path(rec)
    params = _params(
        rec.parameters,
        known_models,
        path=path,
        optional_overrides=optional_overrides,
    )
    if request_model is None:
        request_model = _inferred_request_model(params, known_models)
    method = (rec.method or "GET").upper()
    has_body_param = any(param.location == "body" for param in params)
    request_annotation = request_model
    uses_mapping = False
    if has_body_param and request_annotation is None and not _body_value_params(params):
        request_annotation = "Mapping[str, object]"
        uses_mapping = True

    model_imports = _model_imports(
        request_model=request_model,
        response_model=response_model,
        known_models=known_models,
    )
    if known_models is not None:
        model_imports.update(
            param.annotation
            for param in params
            if param.annotation in known_models and param.annotation != request_model
        )

    return _Binding(
        rec=rec,
        function_name=function_name,
        async_function_name=f"a{function_name}",
        spec_name=endpoint_spec_name(rec),
        method=method,
        path=path,
        host_rooted=is_host_rooted(rec),
        rate_limit_bucket=target_module(rec.target),
        auth_policy=_auth_policy(rec),
        idempotent=_is_idempotent(rec, method),
        params=params,
        request_model=request_model,
        response_model=response_model,
        request_annotation=request_annotation,
        response_annotation=response_model,
        unresolved_response_model=unresolved_response_model,
        uses_mapping=uses_mapping,
        model_imports=model_imports,
        core_model_imports=_core_model_imports(
            response_model,
            unresolved_response_model=unresolved_response_model,
        ),
    )


def _render_module(bindings: list[_Binding]) -> str:
    sorted_bindings = sorted(bindings, key=lambda binding: binding.spec_name)
    lines = _module_header(sorted_bindings)
    target = sorted_bindings[0].rate_limit_bucket if sorted_bindings else "misc"
    lines.insert(
        1,
        render_docstring(
            f"Generated endpoint bindings for the StoneX CIAPI v2 {target} target.", indent=0
        ),
    )
    for index, binding in enumerate(sorted_bindings):
        if index:
            lines.append("\n\n")
        lines.extend(_binding_lines(binding))
    lines.append("\n\n__all__ = [\n")
    for binding in sorted_bindings:
        lines.append(f'    "{binding.spec_name}",\n')
        lines.append(f'    "{binding.function_name}",\n')
        lines.append(f'    "{binding.async_function_name}",\n')
    lines.append("]\n")
    return _annotate_unwrappable_long_lines(format_python("".join(lines)))


def _annotate_unwrappable_long_lines(source: str) -> str:
    """Append ``# noqa: E501`` to formatted lines that overflow the column limit unwrappably.

    A few catalog identifiers are long enough that a ``name: Type`` signature parameter or
    annotation exceeds the 100-column limit even after ``ruff format`` — the line is atomic, so
    the formatter cannot split it. Mirror the resource aggregator's handling of long
    ``import ... as`` lines (see ``emit_client._alias_import``) so generated endpoint modules
    stay lint-clean. Idempotent: lines already carrying a ``# noqa`` are left untouched.
    """

    annotated: list[str] = []
    for line in source.splitlines(keepends=True):
        body = line.rstrip("\n")
        if len(body) > 100 and "# noqa" not in body:
            newline = "\n" if line.endswith("\n") else ""
            annotated.append(f"{body}  # noqa: E501{newline}")
        else:
            annotated.append(line)
    return "".join(annotated)


def _module_header(bindings: list[_Binding]) -> list[str]:
    lines = [
        BANNER,
        "from __future__ import annotations\n\n",
    ]
    if any(binding.uses_mapping for binding in bindings):
        lines.append("from collections.abc import Mapping\n")
    if any(_uses_decimal_default(binding) for binding in bindings):
        lines.append("from decimal import Decimal\n")
    typing_imports: list[str] = []
    unresolved_aliases = _unresolved_response_aliases(bindings)
    if unresolved_aliases:
        typing_imports.append("TypeAlias")
    if typing_imports:
        lines.append(f"from typing import {', '.join(sorted(typing_imports))}\n")
    endpoint_imports = ["AuthPolicy", "EndpointSpec"]
    if any(binding.params for binding in bindings):
        endpoint_imports.append("Param")
    lines.append(f"from stonepy._core.endpoint import {', '.join(endpoint_imports)}\n")
    core_model_imports = sorted(
        {name for binding in bindings for name in binding.core_model_imports}
    )
    if core_model_imports:
        lines.append(f"from stonepy._core.models import {', '.join(core_model_imports)}\n")
    lines.append("from stonepy._core.pipeline import CallContext\n")

    model_imports = sorted(
        {model for binding in bindings for model in binding.model_imports},
    )
    if model_imports:
        lines.append(f"from stonepy.models import {', '.join(model_imports)}\n")
    lines.append("\n")
    for alias in unresolved_aliases:
        lines.append(f"{alias}: TypeAlias = PassthroughResponseModel\n")
    if unresolved_aliases:
        lines.append("\n")
    return lines


def _binding_lines(binding: _Binding) -> list[str]:
    lines = [
        f"{binding.spec_name}: EndpointSpec[{binding.response_annotation}] = EndpointSpec(\n",
        f"    name={_string_literal(binding.rec.name)},\n",
        f"    method={_string_literal(binding.method)},\n",
        f"    path={_string_literal(binding.path)},\n",
    ]
    if binding.host_rooted:
        lines.append("    host_rooted=True,\n")
    lines += [
        f"    idempotent={binding.idempotent},\n",
        f"    auth_policy=AuthPolicy.{binding.auth_policy},\n",
        f"    rate_limit_bucket={_string_literal(binding.rate_limit_bucket)},\n",
        f"    response_model={binding.response_model},\n",
    ]
    if binding.request_model is not None:
        lines.append(f"    request_model={binding.request_model},\n")
    if binding.params:
        lines.append("    params=(\n")
        for param in binding.params:
            lines.append(
                "        Param("
                f"name={_string_literal(param.name)}, "
                f"location={_string_literal(param.location)}, "
                f"python_name={_string_literal(param.python_name)}"
                "),\n"
            )
        lines.append("    ),\n")
    lines.append(")\n\n\n")
    lines.extend(_wrapper_lines(binding, is_async=False))
    lines.append("\n\n")
    lines.extend(_wrapper_lines(binding, is_async=True))
    return lines


def _wrapper_lines(binding: _Binding, *, is_async: bool) -> list[str]:
    function_name = binding.async_function_name if is_async else binding.function_name
    prefix = "async def" if is_async else "def"
    required_params: list[str] = []
    optional_params: list[str] = []
    body_param = _body_param(binding)
    for param in binding.params:
        if param.location in {"path", "query"} or (
            param.location == "body" and binding.request_model is None
        ):
            signature = _signature_param(param)
            if param.optional:
                optional_params.append(signature)
            else:
                required_params.append(signature)
    if body_param is not None:
        required_params.append(body_param)
    signature_params = ["ctx: CallContext", *required_params]
    if optional_params:
        signature_params.append("*")
        signature_params.extend(optional_params)
    lines = [
        f"{prefix} {function_name}(",
        ", ".join(signature_params),
        f") -> {binding.response_annotation}:\n",
        render_docstring(endpoint_summary(binding.rec), indent=4),
    ]

    call = "ctx.ainvoke" if is_async else "ctx.invoke"
    await_prefix = "await " if is_async else ""
    invocation_args = _invocation_args(binding)
    if not invocation_args:
        lines.append(f"    return {await_prefix}{call}({binding.spec_name})\n")
    else:
        lines.append(
            f"    return {await_prefix}{call}({binding.spec_name}, {', '.join(invocation_args)})\n"
        )
    return lines


def _body_param(binding: _Binding) -> str | None:
    if not any(param.location == "body" for param in binding.params):
        return None
    if binding.request_annotation is None:
        return None
    if binding.request_model is not None:
        return f"request: {binding.request_annotation}"
    return f"body: {binding.request_annotation}"


def _invocation_args(binding: _Binding) -> list[str]:
    args: list[str] = []
    path_args = _call_mapping(binding.params, "path")
    query_args = _query_arg(binding)
    if path_args:
        args.append(f"path_params={path_args}")
    if query_args:
        args.append(f"query={query_args}")
    if any(param.location == "body" for param in binding.params):
        if binding.request_model is not None:
            args.append("body=request")
        else:
            body_args = _call_mapping(_body_value_params(binding.params), "body")
            args.append(f"body={body_args}" if body_args else "body=body")
    return args


def _query_arg(binding: _Binding) -> str | None:
    model_params = [
        param
        for param in binding.params
        if param.location == "query" and param.annotation == binding.request_model
    ]
    if len(model_params) == 1:
        param = model_params[0]
        return f'{param.python_name}.model_dump(by_alias=True, exclude_unset=True, mode="python")'
    return _call_mapping(binding.params, "query")


def _body_value_params(params: list[_Param]) -> list[_Param]:
    return [param for param in params if param.location == "body" and param.python_name != "body"]


def _call_mapping(params: list[_Param], location: str) -> str | None:
    pairs = [
        f"{_string_literal(param.name)}: {param.python_name}"
        for param in params
        if param.location == location
    ]
    if not pairs:
        return None
    return "{" + ", ".join(pairs) + "}"


def _render_init(grouped: Mapping[str, list[_Binding]]) -> str:
    # Re-export the target *submodules*, never the binding functions/specs. Re-exporting a
    # function whose name matches a submodule (e.g. ``order``) would shadow that submodule in
    # the package namespace and break ``from stonepy._endpoints import order as _ep``.
    module_names = sorted(grouped)
    lines = [
        BANNER,
        render_docstring(
            "Generated StoneX CIAPI v2 endpoint binding modules, one per API target.", indent=0
        ),
        "from __future__ import annotations\n\n",
    ]
    if module_names:
        lines.append(f"from . import {', '.join(module_names)}\n")
    lines.append("\n__all__ = [\n")
    for module_name in module_names:
        lines.append(f'    "{module_name}",\n')
    lines.append("]\n")
    return format_python("".join(lines))


def _function_name(rec: EndpointRecord) -> str:
    logical_name = rec.logical_name or _VERSION_SUFFIX_RE.sub("", rec.name)
    normalized = field_name(logical_name)
    if normalized is None:
        normalized = "endpoint"
    return normalized


def _auth_policy(rec: EndpointRecord) -> str:
    raw_names = [rec.name, rec.logical_name or ""]
    normalized_names = {re.sub(r"[^0-9a-z]+", "", name.lower()) for name in raw_names}
    if "logon" in normalized_names or (rec.path or "").lower() == "/session/v2/session":
        return "NONE"
    return "SESSION"


def _is_idempotent(rec: EndpointRecord, method: str) -> bool:
    if method in _IDEMPOTENT_METHODS:
        return True
    logical_name = rec.logical_name or _VERSION_SUFFIX_RE.sub("", rec.name)
    return (target_module(rec.target), logical_name) in _RETRY_SAFE_ENDPOINT_OVERRIDES


def _params(
    raw_params: list[dict[str, Any]],
    known_models: set[str] | None,
    *,
    path: str,
    optional_overrides: frozenset[str] = frozenset(),
) -> list[_Param]:
    rendered: list[_Param] = []
    used_names: set[str] = set()
    covered: set[str] = set()
    path_placeholders, query_placeholders = _template_placeholders(path)
    for raw_param in raw_params:
        raw_name = raw_param.get("name")
        if not isinstance(raw_name, str):
            continue
        location = _param_location(
            raw_param,
            raw_name=raw_name,
            path_placeholders=path_placeholders,
            query_placeholders=query_placeholders,
        )
        if location not in {"path", "query", "body"}:
            continue
        python_param_name = field_name(raw_name)
        if python_param_name is None:
            continue
        python_param_name = _unique_name(python_param_name, used_names)
        annotation = _param_annotation(raw_param, known_models)
        optional = location != "path" and (
            (location == "query" and _is_optional_query_param(raw_param))
            or _is_nullable_param(raw_param)
            or raw_name in optional_overrides
        )
        rendered.append(
            _Param(
                name=raw_name,
                location=location,
                python_name=python_param_name,
                annotation=annotation,
                optional=optional,
                default_expr=_param_default_expr(raw_param, annotation) if optional else None,
            )
        )
        covered.add(raw_name.lower())
    rendered.extend(_synthetic_template_params(path, covered, used_names))
    return rendered


def _synthetic_template_params(path: str, covered: set[str], used_names: set[str]) -> list[_Param]:
    """Synthesize params for URI templates the catalog ``parameters`` list omits.

    Some catalog entries (e.g. ``GetMarketSpread v2``) template path/query values but ship an
    empty parameter list; without these the request template can never be filled. Such values
    are raw string substitutions, so they default to required ``str`` params.
    """

    path_template, separator, query_template = path.partition("?")
    extras: list[_Param] = []
    segments = [(path_template, "path")]
    if separator:
        segments.append((query_template, "query"))
    for segment, location in segments:
        for raw_name in _PLACEHOLDER_RE.findall(segment):
            if raw_name.lower() in covered:
                continue
            python_param_name = field_name(raw_name)
            if python_param_name is None:
                continue
            covered.add(raw_name.lower())
            extras.append(
                _Param(
                    name=raw_name,
                    location=location,
                    python_name=_unique_name(python_param_name, used_names),
                    annotation="str",
                    optional=False,
                    default_expr=None,
                )
            )
    return extras


def _unique_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        used_names.add(name)
        return name

    suffix = 2
    while f"{name}_{suffix}" in used_names:
        suffix += 1
    unique = f"{name}_{suffix}"
    used_names.add(unique)
    return unique


def _param_annotation(param: Mapping[str, Any], known_models: set[str] | None) -> str:
    ref = param.get("ref")
    if isinstance(ref, str) and ref:
        if known_models is None:
            return python_name(ref)
        annotation = python_type(param, known_models)
        return "object" if annotation == "Unresolved" else annotation

    annotation = python_type(param, known_models or set())
    return "object" if annotation == "Unresolved" else annotation


def _known_type(type_name: str | None, known_models: set[str] | None) -> str | None:
    if type_name is None:
        return None
    if known_models is None or type_name in known_models:
        return type_name
    return None


def _inferred_request_model(params: list[_Param], known_models: set[str] | None) -> str | None:
    if known_models is None:
        return None
    candidates = [
        param.annotation
        for param in params
        if param.location in {"body", "query"} and param.annotation in known_models
    ]
    return candidates[0] if len(candidates) == 1 else None


def _response_model_type(type_name: str | None, known_models: set[str] | None) -> str:
    if type_name is None:
        return "ResponseModel"
    if known_models is None or type_name in known_models:
        return type_name
    return python_name(type_name)


def _unresolved_response_model(
    type_name: str | None,
    known_models: set[str] | None,
) -> str | None:
    if type_name is None or known_models is None or type_name in known_models:
        return None
    return python_name(type_name)


def _model_imports(
    *,
    request_model: str | None,
    response_model: str,
    known_models: set[str] | None,
) -> set[str]:
    candidates = {name for name in (request_model, response_model) if name is not None}
    if known_models is None:
        return candidates - {"PassthroughResponseModel", "ResponseModel"}
    return {name for name in candidates if name in known_models}


def _core_model_imports(
    response_model: str,
    *,
    unresolved_response_model: str | None,
) -> set[str]:
    imports: set[str] = set()
    if response_model == "ResponseModel":
        imports.add("ResponseModel")
    if unresolved_response_model is not None:
        imports.add("PassthroughResponseModel")
    return imports


def _unresolved_response_aliases(bindings: list[_Binding]) -> list[str]:
    return sorted(
        {
            binding.unresolved_response_model
            for binding in bindings
            if binding.unresolved_response_model is not None
        }
    )


def _uses_decimal_default(binding: _Binding) -> bool:
    return any(
        param.default_expr is not None and "Decimal(" in param.default_expr
        for param in binding.params
    )


def _signature_param(param: _Param) -> str:
    if not param.optional:
        return f"{param.python_name}: {param.annotation}"
    default_expr = param.default_expr or "None"
    return f"{param.python_name}: {param.annotation} | None = {default_expr}"


def _template_placeholders(path: str) -> tuple[set[str], set[str]]:
    path_template, separator, query_template = path.partition("?")
    path_placeholders = {name.lower() for name in _PLACEHOLDER_RE.findall(path_template)}
    query_placeholders = (
        {name.lower() for name in _PLACEHOLDER_RE.findall(query_template)} if separator else set()
    )
    return path_placeholders, query_placeholders


def _param_location(
    raw_param: Mapping[str, Any],
    *,
    raw_name: str,
    path_placeholders: set[str],
    query_placeholders: set[str],
) -> object:
    normalized_name = raw_name.lower()
    if normalized_name in path_placeholders:
        return "path"
    if normalized_name in query_placeholders:
        return "query"
    return raw_param.get("in") or raw_param.get("location")


def _is_optional_query_param(raw_param: Mapping[str, Any]) -> bool:
    raw_type = raw_param.get("type")
    if not isinstance(raw_type, str):
        return False
    normalized = " ".join(raw_type.lower().split())
    return "required false" in normalized or _DEFAULT_VALUE_RE.search(raw_type) is not None


def _is_nullable_param(raw_param: Mapping[str, Any]) -> bool:
    """A ``nullable true`` param is optional: the spec lets the caller omit it.

    The transport drops a ``None`` query value (and a ``None`` query-template segment), so
    nullable query/body params become ``... | None = None`` rather than required positionals.
    """

    raw_type = raw_param.get("type")
    if not isinstance(raw_type, str):
        return False
    return "nullable true" in " ".join(raw_type.lower().split())


def _param_default_expr(raw_param: Mapping[str, Any], annotation: str) -> str | None:
    raw_type = raw_param.get("type")
    if not isinstance(raw_type, str):
        return None
    match = _DEFAULT_VALUE_RE.search(raw_type)
    if match is None:
        return None

    value = match.group(1).strip().rstrip(".,;")
    normalized = value.lower()
    if normalized == "false":
        return "False"
    if normalized == "true":
        return "True"
    if normalized in {"none", "null"}:
        return "None"
    if annotation == "int" and re.fullmatch(r"-?\d+", value):
        return value
    if annotation == "Decimal":
        return f'Decimal("{value}")'
    return json.dumps(value)


def _string_literal(value: str) -> str:
    return json.dumps(value)
