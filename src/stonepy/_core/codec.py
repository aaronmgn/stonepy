"""Decimal-safe JSON and WCF (`/Date(ms)/`) date handling."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, NoReturn, TypeAlias

import simplejson
from pydantic import BeforeValidator, PlainSerializer

WCF_MINVALUE_MS = -62135596800000
_WCF_RE = re.compile(r"\\?/Date\((-?\d+)(?:[+-]\d{4})?\)\\?/")
_UTC_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MS_PER_DAY = 86_400_000
_MS_PER_SECOND = 1_000


def _ensure_timezone_aware(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


def parse_wcf_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_timezone_aware(value)
    if isinstance(value, bool):
        raise ValueError(f"not a WCF date: {value!r}")
    if isinstance(value, int):
        ms = value
    elif isinstance(value, str):
        m = _WCF_RE.fullmatch(value)
        if not m:
            raise ValueError(f"not a WCF date: {value!r}")
        ms = int(m.group(1))
    else:
        raise ValueError(f"not a WCF date: {value!r}")
    if ms == WCF_MINVALUE_MS:
        return None
    try:
        return _UTC_EPOCH + timedelta(milliseconds=ms)
    except OverflowError as exc:
        raise ValueError(f"WCF date out of range: {value!r}") from exc


def format_wcf_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware_value = _ensure_timezone_aware(value)
    delta = aware_value.astimezone(UTC) - _UTC_EPOCH
    ms = (
        delta.days * _MS_PER_DAY
        + delta.seconds * _MS_PER_SECOND
        + delta.microseconds // _MS_PER_SECOND
    )
    return f"/Date({ms})/"


StoneXDateTime: TypeAlias = Annotated[
    datetime | None,
    BeforeValidator(parse_wcf_date),
    PlainSerializer(format_wcf_date, when_used="always"),
]


def _reject_nonfinite_decimals(value: Any) -> None:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal values are not valid JSON")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite_decimals(key)
            _reject_nonfinite_decimals(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_nonfinite_decimals(item)


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")


def dumps(obj: Any) -> str:
    _reject_nonfinite_decimals(obj)
    return simplejson.dumps(obj, use_decimal=True, allow_nan=False, separators=(",", ":"))


def loads(text: str | bytes) -> Any:
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return json.loads(text, parse_float=Decimal, parse_constant=_reject_json_constant)
