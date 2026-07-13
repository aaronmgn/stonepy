"""Command-line entry point for stonepy generator passes."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from stonepy._generator import emit_client, emit_contract, emit_endpoints, emit_models, scaffold
from stonepy._generator.catalog import (
    Catalog,
    assert_allowed_unresolved,
    assert_catalog_frozen,
    load_catalog,
)

_DEFAULT_PACKAGE_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    """Run a generator command."""

    parser = argparse.ArgumentParser(prog="python -m stonepy._generator")
    parser.add_argument(
        "command",
        choices=["models", "endpoints", "contract", "client", "all", "scaffold"],
    )
    parser.add_argument("scaffold_target", nargs="?")
    parser.add_argument("scaffold_endpoint", nargs="?")
    parser.add_argument(
        "--catalog-root",
        type=Path,
        default=None,
        help="Catalog directory (takes precedence over STONEPY_CATALOG).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Legacy output directory for generated package files.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=None,
        help="Package root that receives generated models and endpoints.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root that receives generated contract tests.",
    )
    parser.add_argument(
        "--resources-dir",
        type=Path,
        default=None,
        help="Resource source root for the client aggregation pass.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow scaffold to overwrite existing resource and test stub files.",
    )
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Allow catalog references outside the frozen unresolved allowlist.",
    )
    parser.add_argument(
        "--allow-unfrozen-catalog",
        action="store_true",
        help="Skip CATALOG_VERSION validation for fixture or exploratory catalogs.",
    )
    args = parser.parse_args(argv)

    package_dir = args.package_dir or args.out_dir or _DEFAULT_PACKAGE_DIR
    if args.command != "scaffold":
        if args.scaffold_target is not None or args.scaffold_endpoint is not None:
            parser.error("scaffold target/endpoint are only valid with the scaffold command")
        if args.force:
            parser.error("--force is only valid with the scaffold command")

    if args.command == "client":
        emit_client.emit_client(args.resources_dir or package_dir / "resources", package_dir)
        return 0
    if args.command == "scaffold":
        if args.scaffold_target is None or args.scaffold_endpoint is None:
            parser.error("scaffold requires <target> and <EndpointName>")
        project_root = args.project_root or args.out_dir or _DEFAULT_PROJECT_ROOT
        catalog_root = _resolve_catalog_root(_catalog_root(parser, args.catalog_root))
        catalog = load_catalog(catalog_root)
        _validate_catalog(
            catalog,
            catalog_root,
            allow_unresolved=args.allow_unresolved,
            allow_unfrozen_catalog=args.allow_unfrozen_catalog,
        )
        scaffold.scaffold(
            catalog,
            args.scaffold_target,
            args.scaffold_endpoint,
            package_dir=package_dir,
            project_root=project_root,
            force=args.force,
        )
        return 0

    project_root = args.project_root or args.out_dir or _DEFAULT_PROJECT_ROOT

    catalog_root = _resolve_catalog_root(_catalog_root(parser, args.catalog_root))
    catalog = load_catalog(catalog_root)
    _validate_catalog(
        catalog,
        catalog_root,
        allow_unresolved=args.allow_unresolved,
        allow_unfrozen_catalog=args.allow_unfrozen_catalog,
    )
    if args.command in {"models", "all"}:
        emit_models.emit_all(catalog, package_dir)
    if args.command in {"endpoints", "all"}:
        emit_endpoints.emit_all(catalog, package_dir)
    if args.command in {"contract", "all"}:
        emit_contract.emit_contract_tests(catalog, project_root)
    if args.command == "all":
        emit_client.emit_client(args.resources_dir or package_dir / "resources", package_dir)
    return 0


def _validate_catalog(
    catalog: Catalog,
    catalog_root: Path,
    *,
    allow_unresolved: bool,
    allow_unfrozen_catalog: bool,
) -> None:
    if not allow_unresolved:
        assert_allowed_unresolved(catalog)
    if not allow_unfrozen_catalog:
        assert_catalog_frozen(catalog, catalog_root)


def _catalog_root(parser: argparse.ArgumentParser, cli_root: Path | None) -> Path:
    """Resolve the catalog input from the CLI first, then the environment."""

    if cli_root is not None:
        return cli_root

    env_root = os.environ.get("STONEPY_CATALOG")
    if env_root is not None and env_root.strip():
        return Path(env_root)

    parser.error("catalog root is required: pass --catalog-root PATH or set STONEPY_CATALOG")


def _resolve_catalog_root(root: Path) -> Path:
    """Return the directory containing catalog JSON files."""

    if (root / "endpoints.json").exists() and (root / "data-types.json").exists():
        return root

    nested = root / "catalog"
    if (nested / "endpoints.json").exists() and (nested / "data-types.json").exists():
        return nested

    return root


if __name__ == "__main__":
    raise SystemExit(main())
