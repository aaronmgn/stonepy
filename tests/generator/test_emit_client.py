from __future__ import annotations

import shutil
from pathlib import Path

from stonepy._generator.__main__ import main
from stonepy._generator.emit_client import emit_client

FIX = Path(__file__).parent / "fixtures"


def test_emit_client_writes_sync_async_resources_and_typed_client(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"

    emit_client(FIX / "resources", package_root)

    sync_mixin = package_root / "resources" / "session" / "_sync" / "log_on.py"
    session_init = package_root / "resources" / "session" / "__init__.py"
    client = package_root / "client.py"

    assert sync_mixin.exists()
    sync_text = sync_mixin.read_text(encoding="utf-8")
    assert "def log_on(self) -> str:" in sync_text
    assert "return cast(str, self._ctx.invoke(_LOG_ON_SPEC))" in sync_text

    session_text = session_init.read_text(encoding="utf-8")
    assert "from ._sync.log_on import _LogOnMixin as _SyncLogOnMixin" in session_text
    assert "from .log_on import _LogOnMixin as _AsyncLogOnMixin" in session_text
    assert "class SessionResource(_SyncLogOnMixin, BaseResource):" in session_text
    assert "class AsyncSessionResource(_AsyncLogOnMixin, BaseResource):" in session_text

    client_text = client.read_text(encoding="utf-8")
    assert "from collections.abc import Awaitable, Callable" in client_text
    assert "from stonepy._endpoints import session as _session_ep" in client_text
    assert "from stonepy.models import ApiLogOnRequestDTO" in client_text
    assert "ctx.logon = _config_logon(ctx, config)" in client_text
    assert "ctx.alogon = _async_config_logon(ctx, config)" in client_text
    assert "from stonepy._core.transport import AsyncTransport, SyncTransport" in client_text
    assert "def _build_async_context(" in client_text
    assert "transport = AsyncTransport(config)" in client_text
    assert "class StoneXClient:" in client_text
    assert '"""Synchronous StoneX CIAPI v2 client.' in client_text
    assert "def session(self) -> SessionResource:" in client_text
    assert '"""Close the underlying synchronous HTTP transport."""' in client_text
    assert "class AsyncStoneXClient:" in client_text
    assert '"""Asynchronous StoneX CIAPI v2 client.' in client_text
    assert "def session(self) -> AsyncSessionResource:" in client_text
    assert '"""Close the underlying asynchronous HTTP transport."""' in client_text
    assert "await self._transport.aclose()" in client_text


def test_emit_client_rewrites_endpoint_async_wrappers_without_endpoint_tree(
    tmp_path: Path,
) -> None:
    resources_dir = tmp_path / "resources"
    session_dir = resources_dir / "session"
    session_dir.mkdir(parents=True)
    (session_dir / "log_on.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from stonepy._core.resource import BaseResource",
                "from stonepy._endpoints import session as _ep",
                "from stonepy.models import ApiLogOnRequestDTO, ApiLogOnResponseDTOv2",
                "",
                "",
                "class _LogOnMixin(BaseResource):",
                "    async def log_on(",
                "        self, request: ApiLogOnRequestDTO",
                "    ) -> ApiLogOnResponseDTOv2:",
                "        return await _ep.alog_on(self._ctx, request)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    package_root = tmp_path / "stonepy"

    emit_client(resources_dir, package_root)

    sync_text = (package_root / "resources" / "session" / "_sync" / "log_on.py").read_text(
        encoding="utf-8"
    )
    assert "return _ep.log_on(self._ctx, request)" in sync_text
    assert "_ep.alog_on" not in sync_text


def test_cli_client_writes_client_from_resources_dir(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"

    assert (
        main(
            [
                "client",
                "--resources-dir",
                str(FIX / "resources"),
                "--package-dir",
                str(package_root),
            ]
        )
        == 0
    )

    assert (package_root / "client.py").exists()
    assert (package_root / "resources" / "session" / "__init__.py").exists()


def test_emit_client_skips_output_when_in_place_resources_dir_is_missing(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "stonepy"

    emit_client(package_root / "resources", package_root)

    assert not (package_root / "client.py").exists()
    assert not (package_root / "resources").exists()


def test_cli_all_runs_client_pass_when_resources_dir_is_provided(tmp_path: Path) -> None:
    docs_root = tmp_path / "Docs"
    catalog_root = docs_root / "catalog"
    catalog_root.mkdir(parents=True)
    for filename in ("endpoints.json", "data-types.json", "lookup-codes.json"):
        (catalog_root / filename).write_text((FIX / filename).read_text(encoding="utf-8"))

    project_root = tmp_path / "project"
    package_root = project_root / "src" / "stonepy"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("", encoding="utf-8")

    assert (
        main(
            [
                "all",
                "--catalog-root",
                str(docs_root),
                "--resources-dir",
                str(FIX / "resources"),
                "--package-dir",
                str(package_root),
                "--project-root",
                str(project_root),
                "--allow-unresolved",
                "--allow-unfrozen-catalog",
            ]
        )
        == 0
    )

    assert (package_root / "client.py").exists()
    assert (package_root / "resources" / "session" / "__init__.py").exists()


def test_emit_client_removes_stale_copied_mixins_from_external_source(tmp_path: Path) -> None:
    resources_dir = tmp_path / "resources"
    session_dir = resources_dir / "session"
    session_dir.mkdir(parents=True)
    (session_dir / "log_on.py").write_text(
        (FIX / "resources" / "session" / "log_on.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (session_dir / "stale.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from stonepy._core.resource import BaseResource",
                "",
                "",
                "class _StaleMixin(BaseResource):",
                "    async def stale(self) -> str:",
                '        return "stale"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    package_root = tmp_path / "package" / "stonepy"

    emit_client(resources_dir, package_root)
    (session_dir / "stale.py").unlink()
    emit_client(resources_dir, package_root)

    session_text = (package_root / "resources" / "session" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "_StaleMixin" not in session_text
    assert not (package_root / "resources" / "session" / "stale.py").exists()
    assert not (package_root / "resources" / "session" / "_sync" / "stale.py").exists()


def test_emit_client_removes_stale_copied_resource_target_from_external_source(
    tmp_path: Path,
) -> None:
    resources_dir = tmp_path / "resources"
    session_dir = resources_dir / "session"
    order_dir = resources_dir / "order"
    session_dir.mkdir(parents=True)
    order_dir.mkdir()
    fixture_text = (FIX / "resources" / "session" / "log_on.py").read_text(encoding="utf-8")
    (session_dir / "log_on.py").write_text(fixture_text, encoding="utf-8")
    (order_dir / "log_on.py").write_text(
        fixture_text.replace("_LogOnMixin", "_OrderMixin"), encoding="utf-8"
    )
    package_root = tmp_path / "package" / "stonepy"

    emit_client(resources_dir, package_root)
    shutil.rmtree(order_dir)
    emit_client(resources_dir, package_root)

    assert not (package_root / "resources" / "order").exists()
    resources_text = (package_root / "resources" / "__init__.py").read_text(encoding="utf-8")
    client_text = (package_root / "client.py").read_text(encoding="utf-8")
    assert "OrderResource" not in resources_text
    assert "OrderResource" not in client_text


def test_ci_drift_gate_checks_generated_client_outputs() -> None:
    workflow = Path(__file__).parents[2] / ".github" / "workflows" / "drift.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "src/stonepy/client.py" in text
    assert "src/stonepy/resources" in text
    assert "git status --porcelain --untracked-files=all" in text
