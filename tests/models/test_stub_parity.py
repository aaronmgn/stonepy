"""Companion stubs must describe Pydantic's actual fields, not just compile.

mypy.stubtest also runs in CI, but does not detect a wrong Pydantic field annotation
or alias: these fields are instance data, absent from the runtime class namespace.
"""

from __future__ import annotations

import ast
import importlib
import keyword
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

import stonepy.models as models
from stonepy._generator.render import BANNER

MODELS = Path(models.__file__).parent
_STUB_POLICY = "Extend the generator rather than hand-write a stub."


def _check_stub_inventory(package: Path) -> None:
    model_dir = package / "models"
    expected = {
        path.with_suffix(".pyi")
        for path in model_dir.glob("*.py")
        if path.stem not in {"__init__", "enums"}
    }
    actual = set(package.rglob("*.pyi"))
    assert actual == expected, (
        f"Ungated or missing stubs: unexpected={sorted(actual - expected)}, "
        f"missing={sorted(expected - actual)}. {_STUB_POLICY}"
    )
    for path in sorted(actual):
        assert path.read_text().startswith(BANNER), (
            f"{path}: missing generated banner. {_STUB_POLICY}"
        )


def _check_module_getattr(tree: ast.Module) -> None:
    pending: list[ast.AST] = list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.ClassDef):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.name != "__getattr__", (
                f"module-level __getattr__ is forbidden. {_STUB_POLICY}"
            )
            continue
        # Also reject aliases/assignments and definitions inside TYPE_CHECKING blocks.
        if isinstance(node, ast.Name):
            assert node.id != "__getattr__", (
                f"module-level __getattr__ is forbidden. {_STUB_POLICY}"
            )
        if isinstance(node, ast.alias):
            assert (node.asname or node.name) != "__getattr__", (
                f"module-level __getattr__ is forbidden. {_STUB_POLICY}"
            )
        pending.extend(ast.iter_child_nodes(node))


def _evaluate(node: ast.expr, namespace: dict[str, Any]) -> Any:
    return eval(compile(ast.Expression(node), "<model stub>", "eval"), namespace)


def _check_model_stub(model: type[BaseModel], source: str) -> int:
    tree = ast.parse(source)
    _check_module_getattr(tree)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == [model.__name__], "class set"
    cls = classes[0]
    namespace: dict[str, Any] = {
        "__name__": model.__module__,
        "__package__": "stonepy.models",
        model.__name__: model,
    }
    # Resolve the stub's own imports and type aliases, including forward references.
    # Do not execute the class or any constructor body.
    for node in tree.body:
        declarations = node.body if isinstance(node, ast.If) else [node]
        for declaration in declarations:
            if isinstance(declaration, (ast.Import, ast.ImportFrom, ast.Assign)):
                exec(
                    compile(ast.Module([declaration], type_ignores=[]), "<model stub>", "exec"),
                    namespace,
                )
    assert tuple(_evaluate(base, namespace) for base in cls.bases) == model.__bases__, "bases"
    fields = {
        node.target.id: node
        for node in cls.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert fields.keys() == model.model_fields.keys(), "field set"
    annotations: dict[str, Any] = {}
    for name, node in fields.items():
        annotation = _evaluate(node.annotation, namespace)
        annotations[name] = annotation
        assert node.value is not None, name
        field = FieldInfo.from_annotated_attribute(annotation, _evaluate(node.value, namespace))
        actual = model.model_fields[name]
        for attribute in (
            "annotation",
            "metadata",
            "default",
            "default_factory",
            "alias",
            "validation_alias",
            "serialization_alias",
            "repr",
        ):
            assert getattr(field, attribute) == getattr(actual, attribute), f"{name}.{attribute}"
        assert field.is_required() == actual.is_required(), f"{name}.required"

    constructors = [
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    ]
    aliases = tuple(
        field.alias
        if field.alias and field.alias.isidentifier() and not keyword.iskeyword(field.alias)
        else name
        for name, field in model.model_fields.items()
    )
    signatures = list(dict.fromkeys((aliases, tuple(fields)))) if fields else []
    assert len(constructors) == len(signatures), "constructor count"
    for names, constructor in zip(signatures, constructors, strict=True):
        decorators = ["overload"] if len(signatures) > 1 else []
        assert [ast.unparse(node) for node in constructor.decorator_list] == decorators
        args = constructor.args
        assert [arg.arg for arg in args.args] == ["self"]
        assert not args.posonlyargs and not args.defaults and args.vararg is None
        assert args.kwarg is None, "permissive constructor"
        assert constructor.returns is not None and ast.unparse(constructor.returns) == "None"
        assert len(constructor.body) == 1 and ast.unparse(constructor.body[0]) == "..."
        assert tuple(arg.arg for arg in args.kwonlyargs) == names, "constructor field set"
        for (name, field), arg, default in zip(
            model.model_fields.items(), args.kwonlyargs, args.kw_defaults, strict=True
        ):
            assert arg.annotation is not None
            assert _evaluate(arg.annotation, namespace) == annotations[name], (
                f"{name}.constructor type"
            )
            assert (default is None) == field.is_required(), f"{name}.constructor required"
            assert default is None or ast.unparse(default) == "...", f"{name}.constructor default"

    # Preserve any future public methods/properties and type aliases, too. The only
    # permitted class-level difference is the stub-only constructor declarations.
    runtime = ast.parse(MODELS.joinpath(f"{model.__name__}.py").read_text())
    runtime_cls = next(node for node in runtime.body if isinstance(node, ast.ClassDef))
    assert [ast.dump(node) for node in cls.body if node not in constructors] == [
        ast.dump(node) for node in runtime_cls.body
    ], "class interface"
    assert [ast.dump(node) for node in tree.body if isinstance(node, ast.Assign)] == [
        ast.dump(node) for node in runtime.body if isinstance(node, ast.Assign)
    ], "module type aliases"
    return len(fields)


def test_all_model_stubs_match_runtime() -> None:
    _check_stub_inventory(MODELS.parent)
    runtime_names = {path.stem for path in MODELS.glob("*.py")} - {"__init__", "enums"}
    assert {path.stem for path in MODELS.glob("*.pyi")} == runtime_names, "companion stub set"
    field_count = 0
    for name in sorted(runtime_names):
        module = importlib.import_module(f"stonepy.models.{name}")
        model = getattr(module, name)
        assert getattr(models, name) is model, f"{name} package export"
        assert issubclass(model, BaseModel)
        try:
            field_count += _check_model_stub(model, MODELS.joinpath(f"{name}.pyi").read_text())
        except AssertionError as exc:
            raise AssertionError(f"{name}: {exc}") from exc
    enums = importlib.import_module("stonepy.models.enums")
    enum_names = {
        name
        for name, value in vars(enums).items()
        if isinstance(value, type)
        and value.__module__ == enums.__name__
        and not name.startswith("_")
    }
    assert set(models.__all__) == runtime_names | enum_names, "public exports"
    for name in enum_names:
        assert getattr(models, name) is getattr(enums, name)
    print(
        f"Parity: {len(runtime_names)} models, {field_count} fields, {len(models.__all__)} exports"
    )


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ('user_name: str = Field(alias="UserName")', "", "field set"),
        ("user_name: str = Field", "user_name: int = Field", "user_name.annotation"),
        ('alias="UserName"', 'alias="Wrong"', "user_name.alias"),
        ('Field(alias="UserName")', 'Field(default=None, alias="UserName")', "user_name.default"),
        ("repr=False", "repr=True", "password.repr"),
        ("class ApiLogOnRequestDTO(RequestModel)", "class ApiLogOnRequestDTO(BaseModel)", "bases"),
        ("UserName: str,", "UserName: int,", "user_name.constructor type"),
        ("UserName: str,", "UserName: str = ...,", "user_name.constructor required"),
    ],
)
def test_parity_detects_corrupt_stubs(before: str, after: str, message: str) -> None:
    source = MODELS.joinpath("ApiLogOnRequestDTO.pyi").read_text()
    assert before in source
    source = "from pydantic import BaseModel\n" + source.replace(before, after, 1)
    with pytest.raises(AssertionError, match=message):
        _check_model_stub(models.ApiLogOnRequestDTO, source)


@pytest.mark.parametrize("unexpected", ["_core/models.pyi", "client.pyi", "models/handwritten.pyi"])
def test_stub_inventory_rejects_ungated_stubs(tmp_path: Path, unexpected: str) -> None:
    path = tmp_path / unexpected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(BANNER + "def __getattr__(name: str) -> Any: ...\n")
    with pytest.raises(AssertionError, match="Extend the generator rather than hand-write a stub"):
        _check_stub_inventory(tmp_path)


def test_stub_inventory_requires_generated_banner(tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "Example.py").write_text("class Example: ...\n")
    stub = model_dir / "Example.pyi"
    stub.write_text("class Example: ...\n")
    with pytest.raises(AssertionError, match="missing generated banner.*Extend the generator"):
        _check_stub_inventory(tmp_path)
    stub.write_text(BANNER + stub.read_text())
    _check_stub_inventory(tmp_path)


@pytest.mark.parametrize(
    "fallback",
    [
        "def __getattr__(name: str) -> Any: ...\n",
        "if TYPE_CHECKING:\n    def __getattr__(name: str) -> Any: ...\n",
        "__getattr__ = Any\n",
        "from typing import Any as __getattr__\n",
    ],
)
def test_parity_rejects_module_getattr(fallback: str) -> None:
    source = MODELS.joinpath("ApiLogOnRequestDTO.pyi").read_text() + "\n" + fallback
    with pytest.raises(AssertionError, match="module-level __getattr__ is forbidden"):
        _check_model_stub(models.ApiLogOnRequestDTO, source)
