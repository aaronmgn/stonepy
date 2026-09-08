"""Logging helpers with secret redaction."""

from __future__ import annotations

from collections.abc import Mapping

SECRET_KEYS: frozenset[str] = frozenset(
    {
        "api-key",
        "app-key",
        "app_key",
        "appkey",
        "authorization",
        "cookie",
        "newpassword",
        "password",
        "proxy",
        "proxy-authorization",
        "session",
        "set-cookie",
        "token",
        "twofatoken",
        "x-api-key",
    }
)


def redact(value: str) -> str:
    """Return ``"***"`` for any non-empty string, leaving empty strings unchanged."""
    if not value:
        return value
    return "***"


def safe_repr(obj: object, secret_keys: set[str] | None = None) -> str:
    """Return a ``repr`` of *obj* with secret-named mapping keys replaced by ``"***"``.

    Handles mappings by redacting values whose key name matches
    a default secret name (app key, password, session, ...) or one of the extra *secret_keys*;
    other objects fall back to plain ``repr``.
    """
    keys = _secret_keys(secret_keys)

    if isinstance(obj, Mapping):
        return repr(_redacted_mapping(obj, keys))

    return repr(obj)


def _secret_keys(secret_keys: set[str] | None) -> set[str]:
    keys = set(SECRET_KEYS)
    if secret_keys is not None:
        keys.update(key.lower() for key in secret_keys)
    return keys


def _redacted_mapping(
    mapping: Mapping[object, object], secret_keys: set[str]
) -> dict[object, object]:
    return {k: _redacted_value(k, v, secret_keys) for k, v in mapping.items()}


def _redacted_value(key: object, value: object, secret_keys: set[str]) -> object:
    if isinstance(key, str) and key.lower() in secret_keys:
        return "***"
    return value
