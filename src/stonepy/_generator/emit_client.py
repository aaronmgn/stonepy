"""Emit aggregated resource classes and public client surfaces."""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

from unasync import Rule, unasync_files  # type: ignore[import-untyped]

from stonepy._generator.render import BANNER, field_name, format_python

__all__ = ["emit_client"]

_ASYNC_ENDPOINT_RE = re.compile(r"^async def (a[a-z_][A-Za-z0-9_]*)\(", re.MULTILINE)
_RESOURCE_ASYNC_ENDPOINT_RE = re.compile(r"\b_ep\.(a[a-z_][A-Za-z0-9_]*)\b")


def emit_client(resources_dir: Path, out_dir: Path) -> None:
    """Generate resource aggregators and client classes."""

    if not resources_dir.exists():
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    package_resources_dir = out_dir / "resources"
    package_resources_dir.mkdir(parents=True, exist_ok=True)

    targets = _copy_resource_sources(resources_dir, package_resources_dir)
    resource_targets = [_resource_target(target) for target in targets]

    replacements = {
        "ainvoke": "invoke",
        "alogon": "logon",
        "aset_token": "set_token",
        **_endpoint_replacements(out_dir, resource_targets),
    }
    for target in resource_targets:
        _emit_sync_mixins(target, replacements)
        _emit_resource_init(target)

    (package_resources_dir / "__init__.py").write_text(
        _render_resources_init(resource_targets),
        encoding="utf-8",
    )
    (out_dir / "client.py").write_text(_render_client(resource_targets), encoding="utf-8")


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
        return f"{_class_name(self.name)}Resource"

    @property
    def async_class_name(self) -> str:
        return f"Async{_class_name(self.name)}Resource"

    @property
    def property_name(self) -> str:
        normalized = field_name(self.name)
        if normalized is None:
            raise ValueError(f"invalid resource target name: {self.name!r}")
        return normalized


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
    sync_dir = target.package_dir / "_sync"
    if sync_dir.exists():
        shutil.rmtree(sync_dir)
    sync_dir.mkdir(parents=True, exist_ok=True)
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
    lines = [BANNER, "from __future__ import annotations\n\n"]
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
    lines.extend(_resource_class_lines(target.class_name, sync_bases))
    lines.append("\n\n")
    lines.extend(_resource_class_lines(target.async_class_name, async_bases))
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


def _resource_class_lines(class_name: str, mixin_bases: list[str]) -> list[str]:
    bases = [*mixin_bases, "BaseResource"]
    return [
        f"class {class_name}({', '.join(bases)}):\n",
        "    pass\n",
    ]


def _render_resources_init(targets: list[_ResourceTarget]) -> str:
    lines = [BANNER, "from __future__ import annotations\n\n"]
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
        "from __future__ import annotations\n\n",
        "from collections.abc import Awaitable, Callable\n",
        "from types import TracebackType\n\n",
        "from stonepy._core.resource import BaseResource\n",
        "from stonepy._core.clock import Clock, SystemClock\n",
        "from stonepy._core.config import ClientConfig\n",
        "from stonepy._core.pipeline import CallContext\n",
        "from stonepy._core.plugins import discover_plugin_resources\n",
        "from stonepy._core.ratelimit import BucketedSlidingWindowLimiter\n",
        "from stonepy._core.retry import RetryPolicy\n",
        "from stonepy._core.session import AsyncSessionManager, SessionManager\n",
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
        '    raise RuntimeError("session refresh is not configured")\n',
        "\n\n",
        "def _has_config_credentials(config: ClientConfig) -> bool:\n",
        "    return bool(config.username and config.password and config.app_key)\n",
        "\n\n",
        "def _logon_request(config: ClientConfig) -> ApiLogOnRequestDTO:\n",
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
        "    if not _has_config_credentials(config):\n",
        "        return _missing_logon\n",
        "\n",
        "    def logon() -> tuple[str, str]:\n",
        "        return (\n",
        '            _session_ep.log_on(ctx, _logon_request(config)).session or "",\n',
        "            config.username,\n",
        "        )\n",
        "\n",
        "    return logon\n",
        "\n\n",
        "def _async_config_logon(\n",
        "    ctx: CallContext, config: ClientConfig\n",
        ") -> Callable[[], Awaitable[tuple[str, str]]] | None:\n",
        "    if not _has_config_credentials(config):\n",
        "        return None\n",
        "\n",
        "    async def alogon() -> tuple[str, str]:\n",
        (
            "        return (await _session_ep.alog_on(ctx, "
            '_logon_request(config))).session or "", config.username\n'
        ),
        "\n",
        "    return alogon\n",
        "\n\n",
        "def _load_plugin_resources(\n",
        "    config: ClientConfig, known: set[str]\n",
        ") -> dict[str, type[BaseResource]]:\n",
        "    return discover_plugin_resources(\n",
        "        enable=config.enable_plugins,\n",
        "        allow_overrides=config.allow_overrides,\n",
        "        known=known,\n",
        "    )\n",
        "\n\n",
        "def _build_context(\n",
        "    config: ClientConfig, clock: Clock | None = None\n",
        ") -> tuple[CallContext, SyncTransport]:\n",
        "    real_clock = clock or SystemClock()\n",
        "    transport = SyncTransport(config)\n",
        "    session = SessionManager(real_clock, config.proactive_refresh_seconds)\n",
        "    ctx = CallContext(\n",
        "        config=config,\n",
        "        transport=transport,\n",
        "        session=session,\n",
        "        limiter=BucketedSlidingWindowLimiter(\n",
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
        "    real_clock = clock or SystemClock()\n",
        "    transport = AsyncTransport(config)\n",
        "    session = AsyncSessionManager(real_clock, config.proactive_refresh_seconds)\n",
        "    ctx = CallContext(\n",
        "        config=config,\n",
        "        transport=transport,\n",
        "        session=session,\n",
        "        limiter=BucketedSlidingWindowLimiter(\n",
        "            config.rate_limit_max,\n",
        "            config.rate_limit_window_seconds,\n",
        "            real_clock,\n",
        "        ),\n",
        "        retry=RetryPolicy(config.max_retries),\n",
        "        clock=real_clock,\n",
        "        logon=_missing_logon,\n",
        "    )\n",
        "    ctx.logon = _config_logon(ctx, config)\n",
        "    ctx.alogon = _async_config_logon(ctx, config)\n",
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
    ]
    known = "{" + ", ".join(f'"{target.property_name}"' for target in targets) + "}"
    lines.append(
        "        self._plugins: dict[str, BaseResource] = {\n"
        f"            name: resource(self._ctx)\n"
        f"            for name, resource in _load_plugin_resources(config, {known}).items()\n"
        "        }\n"
    )
    for target in targets:
        resource_type = target.async_class_name if async_client else target.class_name
        lines.append(f"        self._{target.property_name}: {resource_type} | None = None\n")
    lines.append("\n")

    for target in targets:
        resource_type = target.async_class_name if async_client else target.class_name
        lines.extend(
            [
                "    @property\n",
                f"    def {target.property_name}(self) -> {resource_type}:\n",
                f'        """Return the {target.property_name} resource group."""\n',
                f"        if self._{target.property_name} is None:\n",
                f"            self._{target.property_name} = {resource_type}(self._ctx)\n",
                f"        return self._{target.property_name}\n",
                "\n",
            ]
        )

    lines.extend(
        [
            "    def plugin(self, name: str) -> BaseResource:\n",
            '        """Return a loaded plugin resource by name."""\n',
            "        return self._plugins[name]\n",
            "\n",
        ]
    )

    if async_client:
        lines.extend(_async_client_lifecycle(name))
    else:
        lines.extend(_sync_client_lifecycle(name))
    return lines


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


def _endpoint_replacements(out_dir: Path, targets: list[_ResourceTarget]) -> dict[str, str]:
    replacements = _resource_endpoint_replacements(targets)
    endpoints_dir = out_dir / "_endpoints"
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
