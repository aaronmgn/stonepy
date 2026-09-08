"""Client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from math import isfinite
from typing import Any, TypedDict, Unpack
from urllib.parse import urlsplit

from stonepy._core.status import LegacyStatusDecoder, StatusDecoder, default_status_decoder
from stonepy._version import __version__

_DEFAULT_USER_AGENT = f"stonepy/{__version__}"


class ClientConfigOverrides(TypedDict, total=False):
    """Optional keyword overrides accepted by ``ClientConfig.from_env``.

    ``None`` preserves environment values or defaults, except for ``status_decoder``, where
    it explicitly disables business-status checks. Keys match ``ClientConfig`` init fields.
    """

    base_url: str | None
    app_key: str | None
    username: str | None
    password: str | None
    app_version: str | None
    connect_timeout: float | None
    read_timeout: float | None
    write_timeout: float | None
    pool_timeout: float | None
    max_connections: int | None
    verify_tls: bool | None
    proxy: str | None
    user_agent: str | None
    max_retries: int | None
    retry_budget_seconds: float | None
    rate_limit_max: int | None
    rate_limit_window_seconds: float | None
    proactive_refresh_seconds: float | None
    status_decoder: StatusDecoder | LegacyStatusDecoder | None


def _validate_base_url(base_url: str) -> None:
    if not isinstance(base_url, str):
        raise TypeError("base_url must be a string")
    if not base_url.strip() or base_url != base_url.strip():
        raise ValueError("base_url must be non-blank without surrounding whitespace")
    invalid = False
    try:
        parts = urlsplit(base_url)
        invalid = parts.port is not None and not 0 < parts.port <= 65535
    except ValueError:
        invalid = True
    if invalid:
        raise ValueError("base_url must have a valid host and port") from None
    if parts.username is not None or parts.password is not None:
        raise ValueError("base_url must not embed credentials")
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("base_url must use http or https and have a hostname")


def _validate_number(name: str, value: object, *, integer: bool, allow_zero: bool) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (integer and not isinstance(value, int))
    ):
        raise TypeError(f"{name} must be {'an integer' if integer else 'a number'}")
    # int is always finite; avoiding a float conversion also handles very large integers.
    if (isinstance(value, float) and not isfinite(value)) or (
        value < 0 if allow_zero else value <= 0
    ):
        raise ValueError(
            f"{name} must be finite and {'non-negative' if allow_zero else 'positive'}"
        )


@dataclass
class ClientConfig:
    """Configuration for StoneX clients.

    `base_url` is required and points at the CIAPI root. `app_key`, `username`, and `password`
    enable automatic session refresh. Timeout, retry, rate-limit, TLS, proxy, and
    status-decoder fields tune transport behavior. A custom `status_decoder` fully replaces
    stonepy's top-level numeric logic for instruction- and order-domain endpoint specs; it
    receives ``(status, status_reason, *, domain)``; legacy two-argument callables also work.
    SaveOrder's text status and nested order statuses retain stonepy's built-in checks. Passing
    ``None`` disables all business-status checks. Use `from_env()` to read the `STONEX_*`
    environment variables with optional keyword overrides.
    """

    base_url: str
    app_key: str = field(default="", repr=False)
    username: str = ""
    password: str = field(default="", repr=False)
    app_version: str = "stonepy"
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 5.0
    max_connections: int = 20
    verify_tls: bool = True
    proxy: str | None = field(default=None, repr=False)
    user_agent: str = _DEFAULT_USER_AGENT
    max_retries: int = 3
    retry_budget_seconds: float = 30.0
    rate_limit_max: int = 500
    rate_limit_window_seconds: float = 5.0
    proactive_refresh_seconds: float = 1080.0
    status_decoder: StatusDecoder | LegacyStatusDecoder | None = default_status_decoder
    """Optional replacement for top-level numeric instruction/order status decoding."""

    def __post_init__(self) -> None:
        _validate_base_url(self.base_url)
        for name in (
            "connect_timeout",
            "read_timeout",
            "write_timeout",
            "pool_timeout",
            "rate_limit_window_seconds",
            "proactive_refresh_seconds",
        ):
            _validate_number(name, getattr(self, name), integer=False, allow_zero=False)
        for name in ("max_connections", "rate_limit_max", "max_retries"):
            _validate_number(
                name, getattr(self, name), integer=True, allow_zero=name == "max_retries"
            )
        _validate_number(
            "retry_budget_seconds", self.retry_budget_seconds, integer=False, allow_zero=True
        )

    @classmethod
    def from_env(cls, **overrides: Unpack[ClientConfigOverrides]) -> ClientConfig:
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

        known_fields = {f.name for f in fields(cls) if f.init}
        unknown_fields = set(overrides) - known_fields
        if unknown_fields:
            unknown = sorted(unknown_fields)[0]
            raise TypeError(f"unexpected ClientConfig override: {unknown}")

        kwargs: dict[str, Any] = {}
        for name, var in (
            ("base_url", "STONEX_BASE_URL"),
            ("app_key", "STONEX_APP_KEY"),
            ("username", "STONEX_USERNAME"),
            ("password", "STONEX_PASSWORD"),
        ):
            if os.environ.get(var):
                kwargs[name] = os.environ[var]
        for name, value in overrides.items():
            if value is not None or name == "status_decoder":
                kwargs[name] = value
        base_url = kwargs.get("base_url", "")
        if isinstance(base_url, str) and not base_url.strip():
            raise ValueError("base_url is required: set STONEX_BASE_URL or pass base_url=...")
        return cls(**kwargs)
