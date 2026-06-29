"""Client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from importlib.metadata import PackageNotFoundError, version
from typing import Any, TypeVar, cast

from stonepy._core.logging import safe_repr
from stonepy._core.status import StatusDecoder, default_status_decoder

_T = TypeVar("_T")
_FALLBACK_VERSION = "0.2.6"


def _default_user_agent() -> str:
    try:
        package_version = version("stonepy")
    except PackageNotFoundError:
        package_version = _FALLBACK_VERSION
    return f"stonepy/{package_version}"


_DEFAULT_USER_AGENT = _default_user_agent()


@dataclass
class ClientConfig:
    """Configuration for StoneX clients.

    `base_url` is required and points at the CIAPI root. `app_key`, `username`, and
    `password` enable automatic session refresh. Timeout, retry, rate-limit, TLS, proxy,
    plugin, and status-decoder fields tune transport behavior. Use `from_env()` to read the
    `STONEX_*` environment variables with optional keyword overrides.
    """

    base_url: str
    app_key: str = ""
    username: str = ""
    password: str = ""
    app_version: str = "stonepy"
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 5.0
    max_connections: int = 20
    verify_tls: bool = True
    proxy: str | None = None
    user_agent: str = _DEFAULT_USER_AGENT
    max_retries: int = 3
    retry_budget_seconds: float = 30.0
    rate_limit_max: int = 500
    rate_limit_window_seconds: float = 5.0
    proactive_refresh_seconds: float = 1080.0
    status_decoder: StatusDecoder | None = default_status_decoder
    enable_plugins: bool = False
    allow_overrides: tuple[str, ...] = ()

    @classmethod
    def from_env(cls, **overrides: Any) -> ClientConfig:
        """Build a config from ``STONEX_*`` environment variables, with keyword overrides.

        Reads ``STONEX_BASE_URL``, ``STONEX_APP_KEY``, ``STONEX_USERNAME``, and
        ``STONEX_PASSWORD``. Any field may be overridden by keyword. For most fields an
        override of ``None`` is ignored in favor of the environment value or default; the
        exception is ``status_decoder``, where passing ``None`` is honored to disable status
        decoding. ``base_url`` is required.

        Args:
            **overrides: Field values that take precedence over the environment.

        Returns:
            A populated ``ClientConfig``.

        Raises:
            TypeError: If an override names a field that does not exist.
            ValueError: If no ``base_url`` is provided via override or environment.
        """

        known_fields = {field.name for field in fields(cls)}
        unknown_fields = set(overrides) - known_fields
        if unknown_fields:
            unknown = sorted(unknown_fields)[0]
            raise TypeError(f"unexpected ClientConfig override: {unknown}")

        base_url = _override(
            overrides,
            "base_url",
            os.environ.get("STONEX_BASE_URL", ""),
        )
        if not base_url.strip():
            raise ValueError("base_url is required: set STONEX_BASE_URL or pass base_url=...")

        return cls(
            base_url=base_url,
            app_key=_override(overrides, "app_key", os.environ.get("STONEX_APP_KEY", "")),
            username=_override(overrides, "username", os.environ.get("STONEX_USERNAME", "")),
            password=_override(overrides, "password", os.environ.get("STONEX_PASSWORD", "")),
            app_version=_override(overrides, "app_version", "stonepy"),
            connect_timeout=_override(overrides, "connect_timeout", 10.0),
            read_timeout=_override(overrides, "read_timeout", 30.0),
            write_timeout=_override(overrides, "write_timeout", 30.0),
            pool_timeout=_override(overrides, "pool_timeout", 5.0),
            max_connections=_override(overrides, "max_connections", 20),
            verify_tls=_override(overrides, "verify_tls", True),
            proxy=_override(overrides, "proxy", None),
            user_agent=_override(overrides, "user_agent", _DEFAULT_USER_AGENT),
            max_retries=_override(overrides, "max_retries", 3),
            retry_budget_seconds=_override(overrides, "retry_budget_seconds", 30.0),
            rate_limit_max=_override(overrides, "rate_limit_max", 500),
            rate_limit_window_seconds=_override(overrides, "rate_limit_window_seconds", 5.0),
            proactive_refresh_seconds=_override(overrides, "proactive_refresh_seconds", 1080.0),
            status_decoder=_override_nullable(
                overrides,
                "status_decoder",
                default_status_decoder,
            ),
            enable_plugins=_override(overrides, "enable_plugins", False),
            allow_overrides=_override(overrides, "allow_overrides", ()),
        )

    def __repr__(self) -> str:
        """Return a repr with secret fields (app key, password, proxy) redacted."""
        return safe_repr(self)


def _override(overrides: dict[str, Any], name: str, default: _T) -> _T:
    value = overrides.get(name, default)
    if value is None:
        return default
    return cast(_T, value)


def _override_nullable(overrides: dict[str, Any], name: str, default: _T) -> _T | None:
    if name in overrides:
        return cast(_T | None, overrides[name])
    return default
