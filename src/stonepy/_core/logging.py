"""Logging helpers with secret redaction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import is_dataclass
from typing import Protocol, TypeGuard

_DEFAULT_SECRET_KEYS = {"app_key", "appkey", "authorization", "password", "proxy", "session"}


class _DataclassInstance(Protocol):
    __dataclass_fields__: dict[str, object]


def redact(value: str) -> str:
    """Return ``"***"`` for any non-empty string, leaving empty strings unchanged."""
    if not value:
        return value
    return "***"


def safe_repr(obj: object, secret_keys: set[str] | None = None) -> str:
    """Return a ``repr`` of *obj* with secret-named keys or fields replaced by ``"***"``.

    Handles mappings and dataclass instances by redacting values whose key/field name matches
    a default secret name (app key, password, session, ...) or one of the extra *secret_keys*;
    other objects fall back to plain ``repr``.
    """
    keys = _secret_keys(secret_keys)

    if isinstance(obj, Mapping):
        return repr(_redacted_mapping(obj, keys))

    if _is_dataclass_instance(obj):
        return _redacted_dataclass_repr(obj, keys)

    return repr(obj)


def _secret_keys(secret_keys: set[str] | None) -> set[str]:
    keys = set(_DEFAULT_SECRET_KEYS)
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


def _is_dataclass_instance(obj: object) -> TypeGuard[_DataclassInstance]:
    return is_dataclass(obj) and not isinstance(obj, type)


def _redacted_dataclass_repr(obj: _DataclassInstance, secret_keys: set[str]) -> str:
    rendered = ", ".join(
        f"{name}={_redacted_value(name, getattr(obj, name), secret_keys)!r}"
        for name in obj.__dataclass_fields__
    )
    return f"{type(obj).__qualname__}({rendered})"
