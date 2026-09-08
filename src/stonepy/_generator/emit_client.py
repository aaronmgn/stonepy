"""Emit aggregated resource classes and public client surfaces."""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

from unasync import Rule, unasync_files  # type: ignore[import-untyped]

from stonepy._generator.publication import (
    OutputTransaction,
    generation_transaction,
    reject_symlinks,
)
from stonepy._generator.render import BANNER, field_name, format_python, render_docstring

__all__ = ["emit_client"]

_ASYNC_ENDPOINT_RE = re.compile(r"^async def (a[a-z_][A-Za-z0-9_]*)\(", re.MULTILINE)
_RESOURCE_ASYNC_ENDPOINT_RE = re.compile(r"\b_ep\.(a[a-z_][A-Za-z0-9_]*)\b")
_RESOURCE_PROPERTY_ALIASES: dict[str, str] = {
    "clientapplication": "client_application",
    "fixedmargin": "fixed_margin",
    "tradingadvisor": "trading_advisor",
}
_DEPRECATED_RESOURCE_PROPERTIES: dict[str, str] = {
    "order_including_closed": "order.get_order_including_closed",
}


def emit_client(
    resources_dir: Path, out_dir: Path, *, _transaction: OutputTransaction | None = None
) -> None:
    """Generate resource aggregators and client classes."""

    reject_symlinks(resources_dir)
    if not resources_dir.exists():
        return

    with generation_transaction(_transaction) as transaction:
        package_resources_dir = transaction.stage(out_dir / "resources", preserve=True)
        if resources_dir.resolve() == (out_dir / "resources").resolve():
            resources_dir = package_resources_dir

        targets = _copy_resource_sources(resources_dir, package_resources_dir)
        resource_targets = [_resource_target(target) for target in targets]

        replacements = {
            "aclear": "clear",
            "acommit": "commit",
            "ainvoke": "invoke",
            "alogon": "logon",
            "aset_token": "set_token",
            **_endpoint_replacements(transaction.path(out_dir / "_endpoints"), resource_targets),
        }
        for target in resource_targets:
            _emit_sync_mixins(target, replacements)
            _emit_resource_init(target)

        (package_resources_dir / "__init__.py").write_text(
            _render_resources_init(resource_targets),
            encoding="utf-8",
        )
        transaction.stage(out_dir / "client.py", directory=False).write_text(
            _render_client(resource_targets), encoding="utf-8"
        )


class _MixinModule:
    def __init__(self, *, path: Path, module_name: str, class_name: str) -> None:
        self.path = path
        self.module_name = module_name
        self.class_name = class_name


class _ResourceTarget:
    def __init__(self, *, name: str, package_dir: Path, mixins: list[_MixinModule]) -> None:
        self.name = name
        self.package_dir = package_dir
        self.mixins = mixins

    @property
    def class_name(self) -> str:
        """The synchronous resource class name, for example ``MarketResource``."""
        return f"{_class_name(self.name)}Resource"

    @property
    def async_class_name(self) -> str:
        """The asynchronous resource class name, for example ``AsyncMarketResource``."""
        return f"Async{_class_name(self.name)}Resource"

    @property
    def property_name(self) -> str:
        """The snake_case client attribute name, for example ``user_account``."""
        normalized = field_name(self.name)
        if normalized is None:
            raise ValueError(f"invalid resource target name: {self.name!r}")
        return _RESOURCE_PROPERTY_ALIASES.get(normalized, normalized)


def _copy_resource_sources(resources_dir: Path, package_resources_dir: Path) -> list[Path]:
    if not resources_dir.exists():
        return []

    source_targets = {
        item.name
        for item in resources_dir.iterdir()
        if item.is_dir()
        and not item.name.startswith(".")
        and item.name not in {"__pycache__", "_sync"}
    }
    if resources_dir.resolve() != package_resources_dir.resolve():
        for dest_target in package_resources_dir.iterdir():
            if dest_target.is_dir() and dest_target.name not in source_targets:
                shutil.rmtree(dest_target)

    targets: list[Path] = []
    for source_target in sorted(item for item in resources_dir.iterdir() if item.is_dir()):
        if source_target.name.startswith(".") or source_target.name in {"__pycache__", "_sync"}:
            continue
        dest_target = package_resources_dir / source_target.name
        if source_target.resolve() != dest_target.resolve() and dest_target.exists():
            shutil.rmtree(dest_target)
        dest_target.mkdir(parents=True, exist_ok=True)
        targets.append(dest_target)

        for source_file in sorted(source_target.glob("*.py")):
            if source_file.name == "__init__.py":
                continue
            dest_file = dest_target / source_file.name
            if source_file.resolve() != dest_file.resolve():
                shutil.copy2(source_file, dest_file)

    return targets


def _resource_target(package_dir: Path) -> _ResourceTarget:
    mixins = [
        _mixin_module(path)
        for path in sorted(package_dir.glob("*.py"))
        if path.name != "__init__.py"
    ]
    return _ResourceTarget(name=package_dir.name, package_dir=package_dir, mixins=mixins)


def _mixin_module(path: Path) -> _MixinModule:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class_names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name.startswith("_")
        and node.name.endswith("Mixin")
    ]
    if len(class_names) != 1:
        raise ValueError(f"{path} must define exactly one private mixin class")
    return _MixinModule(path=path, module_name=path.stem, class_name=class_names[0])


def _emit_sync_mixins(target: _ResourceTarget, replacements: dict[str, str]) -> None:
    reject_symlinks(target.package_dir)
    with generation_transaction() as transaction:
        sync_dir = transaction.stage(target.package_dir / "_sync")
        if not target.mixins:
            return

        rule = Rule(str(target.package_dir), str(sync_dir), replacements)
        unasync_files([str(mixin.path) for mixin in target.mixins], [rule])
        for sync_file in sorted(sync_dir.glob("*.py")):
            source = sync_file.read_text(encoding="utf-8")
            if not source.startswith(BANNER):
                source = BANNER + source
            sync_file.write_text(format_python(source), encoding="utf-8")


def _emit_resource_init(target: _ResourceTarget) -> None:
    target.package_dir.mkdir(parents=True, exist_ok=True)
    (target.package_dir / "__init__.py").write_text(
        _render_resource_init(target),
        encoding="utf-8",
    )


def _render_resource_init(target: _ResourceTarget) -> str:
    lines = [
        BANNER,
        render_docstring(
            f"Synchronous and asynchronous {target.name} resource group classes.", indent=0
        ),
        "from __future__ import annotations\n\n",
    ]
    lines.append("from stonepy._core.resource import BaseResource\n")
    for mixin in target.mixins:
        lines.append(
            _alias_import(
                f"._sync.{mixin.module_name}", mixin.class_name, f"_Sync{mixin.class_name[1:]}"
            )
        )
        lines.append(
            _alias_import(
                f".{mixin.module_name}", mixin.class_name, f"_Async{mixin.class_name[1:]}"
            )
        )
    lines.append("\n")

    sync_bases = [f"_Sync{mixin.class_name[1:]}" for mixin in target.mixins]
    async_bases = [f"_Async{mixin.class_name[1:]}" for mixin in target.mixins]
    prop = target.property_name
    sync_doc = render_docstring(
        f"Synchronous `{prop}` resource group; access it via `StoneXClient.{prop}`. "
        "Each method maps to one StoneX CIAPI v2 endpoint.",
        indent=4,
    )
    async_doc = render_docstring(
        f"Asynchronous `{prop}` resource group; access it via `AsyncStoneXClient.{prop}`. "
        "Each method is the awaitable twin of the synchronous resource's method.",
        indent=4,
    )
    lines.extend(_resource_class_lines(target.class_name, sync_bases, sync_doc))
    lines.append("\n\n")
    lines.extend(_resource_class_lines(target.async_class_name, async_bases, async_doc))
    lines.append("\n\n__all__ = [\n")
    lines.append(f'    "{target.async_class_name}",\n')
    lines.append(f'    "{target.class_name}",\n')
    lines.append("]\n")
    return format_python("".join(lines))


def _alias_import(module_path: str, class_name: str, alias: str) -> str:
    """Render ``from <module> import <class> as <alias>``.

    Long endpoint names produce alias lines that exceed the line-length limit and cannot be
    wrapped by the formatter (an ``import x as y`` clause is atomic). Emit the formatter-canonical
    parenthesized form with an inner ``# noqa: E501`` so generated output stays lint-clean.
    """

    simple = f"from {module_path} import {class_name} as {alias}"
    if len(simple) <= 100:
        return simple + "\n"
    inner = f"    {class_name} as {alias},"
    noqa = "  # noqa: E501" if len(inner) > 100 else ""
    return f"from {module_path} import (\n{inner}{noqa}\n)\n"


def _resource_class_lines(class_name: str, mixin_bases: list[str], docstring: str) -> list[str]:
    # The class docstring keeps the body non-empty, so the aggregated resource needs no ``pass``.
    bases = [*mixin_bases, "BaseResource"]
    return [
        f"class {class_name}({', '.join(bases)}):\n",
        docstring,
    ]


def _render_resources_init(targets: list[_ResourceTarget]) -> str:
    lines = [
        BANNER,
        render_docstring(
            "Typed resource groups exposed as properties on the StoneX clients.", indent=0
        ),
        "from __future__ import annotations\n\n",
    ]
    for target in targets:
        lines.append(f"from .{target.name} import {target.async_class_name}, {target.class_name}\n")
    exported = sorted(
        [name for target in targets for name in (target.async_class_name, target.class_name)]
    )
    lines.append("\n__all__ = [\n")
    for name in exported:
        lines.append(f'    "{name}",\n')
    lines.append("]\n")
    return format_python("".join(lines))


def _render_client(targets: list[_ResourceTarget]) -> str:
    lines = [
        BANNER,
        render_docstring("Synchronous and asynchronous StoneX CIAPI v2 client classes.", indent=0),
        "from __future__ import annotations\n\n",
        "import warnings\n",
        "from collections.abc import Awaitable, Callable\n",
        "from threading import Lock\n",
        "from types import TracebackType\n\n",
        "from stonepy._core.errors import ConfigurationError\n",
        "from stonepy._core.clock import Clock, SystemClock\n",
        "from stonepy._core.config import ClientConfig\n",
        "from stonepy._core.pipeline import CallContext\n",
        "from stonepy._core.ratelimit import SlidingWindowLimiter\n",
        "from stonepy._core.retry import RetryPolicy\n",
        (
            "from stonepy._core.session import "
            "AsyncSessionManager, SessionManager, require_session_token\n"
        ),
        "from stonepy._core.transport import AsyncTransport, SyncTransport\n",
        "from stonepy._endpoints import session as _session_ep\n",
        "from stonepy.models import ApiLogOnRequestDTO\n",
    ]
    for target in targets:
        lines.append(
            f"from stonepy.resources.{target.name} import "
            f"{target.async_class_name}, {target.class_name}\n"
        )
    lines.append("\n\n")
    lines.extend(_client_helpers())
    lines.append("\n\n")
    lines.extend(_client_class("StoneXClient", targets, async_client=False))
    lines.append("\n\n")
    lines.extend(_client_class("AsyncStoneXClient", targets, async_client=True))
    return format_python("".join(lines))


def _client_helpers() -> list[str]:
    return [
        "def _missing_logon() -> tuple[str, str]:\n",
        '    """Raise because no credentials were configured for session refresh."""\n',
        "    raise ConfigurationError(\n",
        '        "session refresh is not configured: set app_key/username/password on "\n',
        '        "ClientConfig or call client.session.log_on() first"\n',
        "    )\n",
        "\n\n",
        "async def _missing_alogon() -> tuple[str, str]:\n",
        '    """Raise because no credentials were configured for session refresh."""\n',
        "    raise ConfigurationError(\n",
        '        "session refresh is not configured: set app_key/username/password on "\n',
        '        "ClientConfig or call client.session.log_on() first"\n',
        "    )\n",
        "\n\n",
        "def _has_config_credentials(config: ClientConfig) -> bool:\n",
        '    """Return whether the config carries the credentials needed to log on."""\n',
        "    return bool(config.username and config.password and config.app_key)\n",
        "\n\n",
        "def _logon_request(config: ClientConfig) -> ApiLogOnRequestDTO:\n",
        '    """Build the logon request body from the configured credentials."""\n',
        "    return ApiLogOnRequestDTO(\n",
        "        UserName=config.username,\n",
        "        Password=config.password,\n",
        "        AppKey=config.app_key,\n",
        "        AppVersion=config.app_version,\n",
        '        AppComments="",\n',
        "    )\n",
        "\n\n",
        "def _config_logon(\n",
        "    ctx: CallContext, config: ClientConfig\n",
        ") -> Callable[[], tuple[str, str]]:\n",
        '    """Return a synchronous logon callable, or a refusing stub if no credentials."""\n',
        "    if not _has_config_credentials(config):\n",
        "        return _missing_logon\n",
        "\n",
        "    def logon() -> tuple[str, str]:\n",
        "        response = _session_ep.log_on(ctx, _logon_request(config))\n",
        "        return require_session_token(response.session), config.username\n",
        "\n",
        "    return logon\n",
        "\n\n",
        "def _async_config_logon(\n",
        "    ctx: CallContext, config: ClientConfig\n",
        ") -> Callable[[], Awaitable[tuple[str, str]]] | None:\n",
        '    """Return an asynchronous logon callable, or None if no credentials."""\n',
        "    if not _has_config_credentials(config):\n",
        "        return None\n",
        "\n",
        "    async def alogon() -> tuple[str, str]:\n",
        "        response = await _session_ep.alog_on(ctx, _logon_request(config))\n",
        "        return require_session_token(response.session), config.username\n",
        "\n",
        "    return alogon\n",
        "\n\n",
        "def _build_context(\n",
        "    config: ClientConfig, clock: Clock | None = None\n",
        ") -> tuple[CallContext, SyncTransport]:\n",
        '    """Assemble the synchronous call context and transport from a config."""\n',
        "    real_clock = clock or SystemClock()\n",
        "    transport = SyncTransport(config)\n",
        "    session = SessionManager(real_clock, config.proactive_refresh_seconds)\n",
        "    ctx = CallContext(\n",
        "        config=config,\n",
        "        transport=transport,\n",
        "        session=session,\n",
        "        limiter=SlidingWindowLimiter(\n",
        "            config.rate_limit_max,\n",
        "            config.rate_limit_window_seconds,\n",
        "            real_clock,\n",
        "        ),\n",
        "        retry=RetryPolicy(config.max_retries),\n",
        "        clock=real_clock,\n",
        "        logon=_missing_logon,\n",
        "    )\n",
        "    ctx.logon = _config_logon(ctx, config)\n",
        "    return ctx, transport\n",
        "\n\n",
        "def _build_async_context(\n",
        "    config: ClientConfig, clock: Clock | None = None\n",
        ") -> tuple[CallContext, AsyncTransport]:\n",
        '    """Assemble the asynchronous call context and transport from a config."""\n',
        "    real_clock = clock or SystemClock()\n",
        "    transport = AsyncTransport(config)\n",
        "    session = AsyncSessionManager(real_clock, config.proactive_refresh_seconds)\n",
        "    ctx = CallContext(\n",
        "        config=config,\n",
        "        transport=transport,\n",
        "        session=session,\n",
        "        limiter=SlidingWindowLimiter(\n",
        "            config.rate_limit_max,\n",
        "            config.rate_limit_window_seconds,\n",
        "            real_clock,\n",
        "        ),\n",
        "        retry=RetryPolicy(config.max_retries),\n",
        "        clock=real_clock,\n",
        "        logon=_missing_logon,\n",
        "    )\n",
        "    ctx.logon = _config_logon(ctx, config)\n",
        "    ctx.alogon = _async_config_logon(ctx, config) or _missing_alogon\n",
        "    return ctx, transport\n",
    ]


def _client_class(name: str, targets: list[_ResourceTarget], *, async_client: bool) -> list[str]:
    class_doc = (
        '    """Asynchronous StoneX CIAPI v2 client.\n\n'
        "    Use with ``async with`` or call ``aclose()`` when finished. Resource properties\n"
        "    mirror the synchronous client and expose awaitable methods.\n"
        '    """\n'
        if async_client
        else '    """Synchronous StoneX CIAPI v2 client.\n\n'
        "    Use as a context manager or call ``close()`` when finished. Resource properties\n"
        "    lazily construct typed API resource groups.\n"
        '    """\n'
    )
    lines = [
        f"class {name}:\n",
        class_doc,
        "    def __init__(self, config: ClientConfig) -> None:\n",
        (
            "        self._ctx, self._transport = _build_async_context(config)\n"
            if async_client
            else "        self._ctx, self._transport = _build_context(config)\n"
        ),
        "        self._resource_lock = Lock()\n",
    ]
    for target in targets:
        resource_type = target.async_class_name if async_client else target.class_name
        lines.append(f"        self._{target.property_name}: {resource_type} | None = None\n")
    lines.extend(
        [
            "\n",
            "    @property\n",
            "    def call_context(self) -> CallContext:\n",
            '        """Return shared call state for explicitly constructed resources.\n\n',
            "        This property cannot be reassigned; its context contains mutable state.\n",
            "        Use it only while this client is open.\n",
            '        """\n',
            "        return self._ctx\n",
            "\n",
        ]
    )

    for target in targets:
        resource_type = target.async_class_name if async_client else target.class_name
        lines.extend(
            [
                "    @property\n",
                f"    def {target.property_name}(self) -> {resource_type}:\n",
                f'        """Return the {target.property_name} resource group."""\n',
                *(
                    _deprecation_warning(
                        name,
                        target.property_name,
                        f"client.{_DEPRECATED_RESOURCE_PROPERTIES[target.property_name]}",
                    )
                    if target.property_name in _DEPRECATED_RESOURCE_PROPERTIES
                    else []
                ),
                f"        if self._{target.property_name} is None:\n",
                "            with self._resource_lock:\n",
                f"                if self._{target.property_name} is None:\n",
                f"                    self._{target.property_name} = {resource_type}(self._ctx)\n",
                f"        return self._{target.property_name}\n",
                "\n",
            ]
        )
        if target.name in _RESOURCE_PROPERTY_ALIASES:
            lines.extend(
                [
                    "    @property\n",
                    f"    def {target.name}(self) -> {resource_type}:\n",
                    f'        """Deprecated alias of ``{target.property_name}``."""\n',
                    *_deprecation_warning(name, target.name, target.property_name),
                    f"        return self.{target.property_name}\n",
                    "\n",
                ]
            )

    if async_client:
        lines.extend(_async_client_lifecycle(name))
    else:
        lines.extend(_sync_client_lifecycle(name))
    return lines


def _deprecation_warning(client_name: str, old: str, replacement: str) -> list[str]:
    return [
        "        warnings.warn(\n",
        f'            "{client_name}.{old} is deprecated; "\n',
        f'            "use {replacement}",\n',
        "            DeprecationWarning,\n",
        "            stacklevel=2,\n",
        "        )\n",
    ]


def _sync_client_lifecycle(name: str) -> list[str]:
    return [
        f"    def __enter__(self) -> {name}:\n",
        '        """Enter the synchronous client context."""\n',
        "        return self\n",
        "\n",
        "    def __exit__(\n",
        "        self,\n",
        "        exc_type: type[BaseException] | None,\n",
        "        exc: BaseException | None,\n",
        "        traceback: TracebackType | None,\n",
        "    ) -> None:\n",
        '        """Close the synchronous client context."""\n',
        "        self.close()\n",
        "\n",
        "    def close(self) -> None:\n",
        '        """Close the underlying synchronous HTTP transport."""\n',
        "        self._transport.close()\n",
    ]


def _async_client_lifecycle(name: str) -> list[str]:
    return [
        f"    async def __aenter__(self) -> {name}:\n",
        '        """Enter the asynchronous client context."""\n',
        "        return self\n",
        "\n",
        "    async def __aexit__(\n",
        "        self,\n",
        "        exc_type: type[BaseException] | None,\n",
        "        exc: BaseException | None,\n",
        "        traceback: TracebackType | None,\n",
        "    ) -> None:\n",
        '        """Close the asynchronous client context."""\n',
        "        await self.aclose()\n",
        "\n",
        "    async def aclose(self) -> None:\n",
        '        """Close the underlying asynchronous HTTP transport."""\n',
        "        await self._transport.aclose()\n",
    ]


def _endpoint_replacements(endpoints_dir: Path, targets: list[_ResourceTarget]) -> dict[str, str]:
    replacements = _resource_endpoint_replacements(targets)
    if not endpoints_dir.exists():
        return replacements
    for endpoint_file in sorted(endpoints_dir.glob("*.py")):
        if endpoint_file.name == "__init__.py":
            continue
        text = endpoint_file.read_text(encoding="utf-8")
        for async_name in _ASYNC_ENDPOINT_RE.findall(text):
            replacements[async_name] = async_name[1:]
    return replacements


def _resource_endpoint_replacements(targets: list[_ResourceTarget]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for target in targets:
        for mixin in target.mixins:
            text = mixin.path.read_text(encoding="utf-8")
            for async_name in _RESOURCE_ASYNC_ENDPOINT_RE.findall(text):
                replacements[async_name] = async_name[1:]
    return replacements


def _class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)
