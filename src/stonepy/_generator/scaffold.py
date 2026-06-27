"""Scaffold hand-authored resource methods and matching test stubs."""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path
from typing import TypeAlias

from stonepy._generator.catalog import Catalog, EndpointRecord
from stonepy._generator.emit_endpoints import render_binding, target_module
from stonepy._generator.render import field_name, format_python

__all__ = ["scaffold"]

_VERSION_SUFFIX_RE = re.compile(r"\s+v\d+\s*$", re.IGNORECASE)
_PATH_PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CORE_MODEL_NAMES = {"PassthroughResponseModel", "ResponseModel"}

_ImportSet: TypeAlias = dict[str, set[str]]


def scaffold(
    catalog: Catalog,
    target: str,
    endpoint_name: str,
    *,
    package_dir: Path,
    project_root: Path,
    force: bool = False,
) -> None:
    """Write a resource mixin and test stub for one catalog endpoint."""

    rec = _find_endpoint(catalog, target, endpoint_name)
    known_model_names = {datatype.name for datatype in catalog.datatypes}
    rendered_binding = render_binding(rec, known_model_names=known_model_names)
    wrapper = _async_wrapper(rendered_binding)
    method_name = wrapper.name[1:] if wrapper.name.startswith("a") else wrapper.name
    resource_target = target_module(rec.target)

    resource_path = package_dir / "resources" / resource_target / f"{method_name}.py"
    test_path = project_root / "tests" / "resources" / resource_target / f"test_{method_name}.py"
    existing_paths = [path for path in (resource_path, test_path) if path.exists()]
    if existing_paths and not force:
        raise FileExistsError(f"refusing to overwrite existing scaffold file: {existing_paths[0]}")

    resource_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.parent.mkdir(parents=True, exist_ok=True)
    resource_path.write_text(
        _render_resource(rec, resource_target, method_name, wrapper, known_model_names),
        encoding="utf-8",
    )
    test_path.write_text(
        _render_test_stub(rec, resource_target, method_name, wrapper, known_model_names),
        encoding="utf-8",
    )


def _find_endpoint(catalog: Catalog, target: str, endpoint_name: str) -> EndpointRecord:
    normalized_target = target_module(target)
    normalized_endpoint = _endpoint_lookup_name(endpoint_name)
    for rec in catalog.endpoints:
        if target_module(rec.target) != normalized_target:
            continue
        if _endpoint_lookup_name(rec.logical_name or rec.name) == normalized_endpoint:
            return rec
        if _endpoint_lookup_name(rec.name) == normalized_endpoint:
            return rec
    raise ValueError(f"endpoint not found: {target}.{endpoint_name}")


def _endpoint_lookup_name(name: str) -> str:
    normalized = field_name(_VERSION_SUFFIX_RE.sub("", name))
    return normalized or ""


def _async_wrapper(source: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(source)
    wrappers = [
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("a")
    ]
    if len(wrappers) != 1:
        raise ValueError("rendered endpoint binding must contain exactly one async wrapper")
    return wrappers[0]


def _render_resource(
    rec: EndpointRecord,
    resource_target: str,
    method_name: str,
    wrapper: ast.AsyncFunctionDef,
    known_model_names: set[str],
) -> str:
    signature = _method_signature(method_name, wrapper)
    call_args = _wrapper_call_args(wrapper)
    imports = _imports_for_function(wrapper, known_model_names, include_return=True)
    _add_unresolved_response_imports(imports, rec, resource_target, wrapper, known_model_names)
    lines = [
        f'"""Resource method: {rec.name}."""\n\n',
        "from __future__ import annotations\n\n",
    ]
    lines.extend(_import_lines(imports))
    lines.extend(
        [
            "from stonepy._core.resource import BaseResource\n",
            f"from stonepy._endpoints import {resource_target} as _ep\n",
        ]
    )
    lines.extend(
        [
            "\n\n",
            f"class {_mixin_class_name(method_name)}(BaseResource):\n",
            f"    {signature}:\n",
            _docstring_lines(_docstring(rec)),
            f"        return await _ep.{wrapper.name}(self._ctx{call_args})\n",
        ]
    )
    return format_python("".join(lines))


def _render_test_stub(
    rec: EndpointRecord,
    resource_target: str,
    method_name: str,
    wrapper: ast.AsyncFunctionDef,
    known_model_names: set[str],
) -> str:
    imports = _imports_for_function(wrapper, known_model_names, include_return=False)
    response_json = "{}"
    method = (rec.method or "GET").lower()
    url = "https://api.example" + _stub_path(rec.path or rec.uri_template or "")
    setup_lines, call_args = _test_call_setup(wrapper, known_model_names)
    lines = [
        "from __future__ import annotations\n\n",
        "import httpx\n",
        "import pytest\n",
        "import respx\n\n",
        "from stonepy.client import StoneXClient\n",
    ]
    lines.extend(_import_lines(imports))
    lines.append("from stonepy._core.config import ClientConfig\n")
    lines.extend(
        [
            "\n\n",
            '@pytest.mark.skip("Fill request values and response payload before enabling.")\n',
            "@respx.mock\n",
            f"def test_{method_name}_returns_response() -> None:\n",
            f'    respx.{method}("{url}").mock(\n',
            f"        return_value=httpx.Response(200, json={response_json})\n",
            "    )\n",
            '    client = StoneXClient(ClientConfig(base_url="https://api.example"))\n',
            "    try:\n",
        ]
    )
    lines.extend(f"        {line}\n" for line in setup_lines)
    lines.extend(
        [
            f"        resp = client.{resource_target}.{method_name}({call_args})\n",
            "        assert resp is not None\n",
            "    finally:\n",
            "        client.close()\n",
        ]
    )
    return format_python("".join(lines))


def _method_signature(method_name: str, wrapper: ast.AsyncFunctionDef) -> str:
    params = [_render_arg(arg, default) for arg, default in _positional_args(wrapper)]
    kwonly = [_render_arg(arg, default) for arg, default in _keyword_only_args(wrapper)]
    if kwonly:
        params.append("*")
        params.extend(kwonly)
    returns = ast.unparse(wrapper.returns) if wrapper.returns is not None else "object"
    return f"async def {method_name}(self, {', '.join(params)}) -> {returns}"


def _positional_args(wrapper: ast.AsyncFunctionDef) -> list[tuple[ast.arg, ast.expr | None]]:
    args = wrapper.args.args[1:]
    defaults: list[ast.expr | None] = [None] * (len(args) - len(wrapper.args.defaults))
    defaults.extend(wrapper.args.defaults)
    return list(zip(args, defaults, strict=True))


def _keyword_only_args(wrapper: ast.AsyncFunctionDef) -> list[tuple[ast.arg, ast.expr | None]]:
    return list(zip(wrapper.args.kwonlyargs, wrapper.args.kw_defaults, strict=True))


def _render_arg(arg: ast.arg, default: ast.expr | None) -> str:
    annotation = ast.unparse(arg.annotation) if arg.annotation is not None else "object"
    rendered = f"{arg.arg}: {annotation}"
    if default is not None:
        rendered += f" = {ast.unparse(default)}"
    return rendered


def _wrapper_call_args(wrapper: ast.AsyncFunctionDef) -> str:
    positional = [arg.arg for arg, _ in _positional_args(wrapper)]
    keyword_only = [f"{arg.arg}={arg.arg}" for arg, _ in _keyword_only_args(wrapper)]
    args = [*positional, *keyword_only]
    if not args:
        return ""
    return ", " + ", ".join(args)


def _test_call_setup(
    wrapper: ast.AsyncFunctionDef,
    known_model_names: set[str],
) -> tuple[list[str], str]:
    setup: list[str] = []
    call_args: list[str] = []
    for arg, _ in _positional_args(wrapper):
        setup.append(_setup_assignment(arg, known_model_names))
        call_args.append(arg.arg)
    for arg, _ in _keyword_only_args(wrapper):
        setup.append(_setup_assignment(arg, known_model_names))
        call_args.append(f"{arg.arg}={arg.arg}")
    return setup, ", ".join(call_args)


def _setup_assignment(arg: ast.arg, known_model_names: set[str]) -> str:
    value = _sample_value(arg, known_model_names)
    # An empty-list sample needs an explicit annotation under mypy --strict (the element type
    # cannot be inferred from ``[]``); other samples are concrete and infer fine.
    if arg.annotation is not None and _is_list_annotation(arg.annotation):
        return f"{arg.arg}: {ast.unparse(arg.annotation)} = {value}"
    return f"{arg.arg} = {value}"


def _sample_value(arg: ast.arg, known_model_names: set[str]) -> str:
    if arg.annotation is not None and _is_list_annotation(arg.annotation):
        return "[]"
    annotation = ast.unparse(arg.annotation) if arg.annotation is not None else "object"
    tokens = set(_TOKEN_RE.findall(annotation))
    model_tokens = sorted(tokens & known_model_names)
    if model_tokens:
        return f"{model_tokens[0]}.model_construct()"
    if "list" in tokens:
        return "[]"
    if "str" in tokens:
        return '"x"'
    if "bool" in tokens:
        return "False"
    if "int" in tokens:
        return "1"
    if "Decimal" in tokens:
        return 'Decimal("1")'
    return "None"


def _is_list_annotation(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Subscript):
        return _annotation_name(annotation.value) == "list"
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _is_list_annotation(annotation.left) or _is_list_annotation(annotation.right)
    return _annotation_name(annotation) == "list"


def _annotation_name(annotation: ast.expr) -> str:
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    return ""


def _imports_for_function(
    wrapper: ast.AsyncFunctionDef,
    known_model_names: set[str],
    *,
    include_return: bool,
) -> _ImportSet:
    imports: _ImportSet = {}
    text_parts: list[str] = []
    defaults: list[str] = []
    for arg, _ in [*_positional_args(wrapper), *_keyword_only_args(wrapper)]:
        if arg.annotation is not None:
            text_parts.append(ast.unparse(arg.annotation))
    for _, default in [*_positional_args(wrapper), *_keyword_only_args(wrapper)]:
        if default is not None:
            defaults.append(ast.unparse(default))
    if include_return and wrapper.returns is not None:
        text_parts.append(ast.unparse(wrapper.returns))
    tokens = set().union(*(_TOKEN_RE.findall(part) for part in [*text_parts, *defaults]))
    _add_imports(imports, "stonepy.models", tokens & known_model_names)
    _add_imports(imports, "stonepy._core.models", tokens & _CORE_MODEL_NAMES)
    if "Decimal" in tokens:
        _add_imports(imports, "decimal", {"Decimal"})
    if "Mapping" in tokens:
        _add_imports(imports, "collections.abc", {"Mapping"})
    if "StoneXDateTime" in tokens:
        _add_imports(imports, "stonepy._core.codec", {"StoneXDateTime"})
    return imports


def _add_unresolved_response_imports(
    imports: _ImportSet,
    rec: EndpointRecord,
    resource_target: str,
    wrapper: ast.AsyncFunctionDef,
    known_model_names: set[str],
) -> None:
    if rec.response_type is None or rec.response_type in known_model_names:
        return
    if wrapper.returns is None or _annotation_name(wrapper.returns) != rec.response_type:
        return
    _add_imports(imports, f"stonepy._endpoints.{resource_target}", {rec.response_type})


def _add_imports(imports: _ImportSet, module: str, names: set[str]) -> None:
    if not names:
        return
    imports.setdefault(module, set()).update(names)


def _import_lines(imports: _ImportSet) -> list[str]:
    return [
        f"from {module} import {', '.join(sorted(names))}\n"
        for module, names in sorted(imports.items())
    ]


def _mixin_class_name(method_name: str) -> str:
    return "_" + "".join(part.capitalize() for part in method_name.split("_")) + "Mixin"


def _docstring(rec: EndpointRecord) -> str:
    if rec.description:
        text = rec.description.strip()
        text = re.sub(
            r"\s*For a more comprehensive order response,\s+see the HTTP service\s+\.",
            "",
            text,
        )
        return (text or f"Call {rec.name}.").replace('"""', '\\"\\"\\"')
    return f"Call {rec.name}."


def _docstring_lines(text: str) -> str:
    wrapped = textwrap.wrap(text, width=82) or [""]
    if len(wrapped) == 1:
        return f'        """{wrapped[0]}"""\n'
    lines = ['        """\n']
    lines.extend(f"        {line}\n" for line in wrapped)
    lines.append('        """\n')
    return "".join(lines)


def _stub_path(path: str) -> str:
    path_only = path.partition("?")[0]
    return _PATH_PLACEHOLDER_RE.sub("1", path_only)
