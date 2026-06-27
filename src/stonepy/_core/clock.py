"""Clock abstraction so timing logic is testable with a fake clock."""

from __future__ import annotations

import asyncio
import time
from typing import Protocol, runtime_checkable


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


@runtime_checkable
class AsyncClock(Clock, Protocol):
    async def asleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    async def asleep(self, seconds: float) -> None:
        if seconds > 0:
            await asyncio.sleep(seconds)


class FakeClock:
    def __init__(self) -> None:
        self._t = 0.0

    def now(self) -> float:
        return self._t

    def sleep(self, seconds: float) -> None:
        self._t += max(0.0, seconds)

    async def asleep(self, seconds: float) -> None:
        self.sleep(seconds)

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        self._t += seconds
