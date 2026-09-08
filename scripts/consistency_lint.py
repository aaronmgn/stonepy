"""Validate hand-authored resource mixin shape."""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path

from stonepy._generator.catalog import (
    assert_allowed_unresolved,
    assert_catalog_frozen,
    load_catalog,
)
from stonepy._generator.validate_overrides import assert_override_consumption

_SNAKE_CASE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def check_resources(resources_dir: Path) -> list[str]:
    """Return resource consistency errors under *resources_dir*."""

    if not resources_dir.exists():
        return [f"resources ERROR: {resources_dir} does not exist"]

    errors: list[str] = []
    modules = sorted(path for path in resources_dir.glob("*/*.py") if path.name != "__init__.py")
    if not modules:
        return [f"resources ERROR: {resources_dir} contains no resource modules"]
    for path in modules:
        errors.extend(_check_resource_file(path))
    return errors


def check_catalog_unresolved(catalog_root: Path, *, validate_overrides: bool = True) -> list[str]:
    root = _resolve_catalog_root(catalog_root)
    missing = [
        filename
        for filename in ("endpoints.json", "data-types.json")
        if not (root / filename).is_file()
    ]
    if not (root / "lookup-codes.json").is_file() and not (root / "lookups.json").is_file():
        missing.append("lookup-codes.json (or lookups.json)")
    if missing:
        return [f"catalog checks ERROR: {root} is missing required file(s): {', '.join(missing)}"]
    try:
        catalog = load_catalog(root)
        assert_allowed_unresolved(catalog)
        assert_catalog_frozen(catalog, root)
        if validate_overrides:
            assert_override_consumption(catalog)
    except (OSError, ValueError) as exc:
        return [f"catalog checks ERROR for {root}: {exc}"]
    return []


def _check_resource_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"{path}: syntax error: {exc.msg}"]

    mixins = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name.startswith("_")
        and node.name.endswith("Mixin")
    ]
    if len(mixins) != 1:
        return [f"{path}: must define exactly one private *Mixin class"]

    mixin = mixins[0]
    errors: list[str] = []
    if not any(_base_name(base) == "BaseResource" for base in mixin.bases):
        errors.append(f"{path}: {mixin.name} must subclass BaseResource")

    public_methods = [
        node
        for node in mixin.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]
    if len(public_methods) != 1:
        errors.append(f"{path}: mixin must define exactly one public method")
        return errors

    method_name = public_methods[0].name
    expected_name = path.stem
    if not _SNAKE_CASE_RE.fullmatch(method_name):
        errors.append(f"{path}: public method must be snake_case")
    if method_name != expected_name:
        errors.append(f"{path}: public method must be named {expected_name}")
    return errors


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "resources_dir", nargs="?", type=Path, default=Path("src/stonepy/resources")
    )
    parser.add_argument(
        "--skip-override-validation",
        action="store_true",
        help="Skip production override-consumption validation for fixture catalogs.",
    )
    args = parser.parse_args(argv or [])
    resources_dir = args.resources_dir
    errors = check_resources(resources_dir)
    catalog_root = os.environ.get("STONEPY_CATALOG", "").strip()
    if catalog_root:
        errors.extend(
            check_catalog_unresolved(
                Path(catalog_root), validate_overrides=not args.skip_override_validation
            )
        )
    else:
        print("catalog checks SKIPPED (STONEPY_CATALOG not set)", file=sys.stderr)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


def _resolve_catalog_root(root: Path) -> Path:
    if (root / "endpoints.json").exists() and (root / "data-types.json").exists():
        return root
    nested = root / "catalog"
    if nested.is_dir():
        return nested
    return root


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
