"""Clock abstraction so timing logic is testable with a fake clock."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


def system_utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


class Clock(Protocol):
    """Minimal time source so timing logic can be driven by a fake clock in tests."""

    def now(self) -> float:
        """Return a monotonic time reference, in seconds."""
        ...

    def sleep(self, seconds: float) -> None:
        """Block the current thread for *seconds*."""
        ...


@runtime_checkable
class AsyncClock(Clock, Protocol):
    """A [`Clock`][stonepy._core.clock.Clock] that can also sleep without blocking the loop."""

    async def asleep(self, seconds: float) -> None:
        """Await *seconds* without blocking the event loop."""
        ...


class SystemClock:
    """Real clock backed by ``time.monotonic`` and ``time``/``asyncio`` sleeps."""

    def now(self) -> float:
        """Return the current monotonic time, in seconds."""
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        """Block for *seconds* (a no-op for non-positive values)."""
        if seconds > 0:
            time.sleep(seconds)

    async def asleep(self, seconds: float) -> None:
        """Await *seconds* (a no-op for non-positive values)."""
        if seconds > 0:
            await asyncio.sleep(seconds)


class FakeClock:
    """Deterministic clock for tests: ``sleep`` advances virtual time instead of waiting."""

    def __init__(self, *, utc_start: datetime | None = None) -> None:
        origin = utc_start if utc_start is not None else datetime(2020, 1, 1, tzinfo=UTC)
        if origin.utcoffset() is None:
            raise ValueError("utc_start must be timezone-aware")
        self._utc_start = origin
        self._t = 0.0

    def utcnow(self) -> datetime:
        """Return the UTC origin advanced by virtual elapsed time."""
        return self._utc_start + timedelta(seconds=self._t)

    def now(self) -> float:
        """Return the current virtual time, in seconds."""
        return self._t

    def sleep(self, seconds: float) -> None:
        """Advance virtual time by *seconds* (clamped to non-negative)."""
        self._t += max(0.0, seconds)

    async def asleep(self, seconds: float) -> None:
        """Advance virtual time by *seconds*, the awaitable form of ``sleep``."""
        self.sleep(seconds)

    def advance(self, seconds: float) -> None:
        """Advance virtual time by *seconds* without consuming a sleep.

        Raises:
            ValueError: If *seconds* is negative.
        """
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        self._t += seconds
