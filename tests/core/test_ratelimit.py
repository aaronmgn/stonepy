import asyncio
import inspect
import threading
from collections.abc import Callable

import pytest

from stonepy._core import ratelimit
from stonepy._core.clock import FakeClock, SystemClock
from stonepy._core.ratelimit import (
    BucketedSlidingWindowLimiter,
    SlidingWindowLimiter,
    backoff_delay,
)


class PartialSleepClock:
    def __init__(self) -> None:
        self._t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self._t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if len(self.sleeps) == 1:
            self._t += seconds / 2.0
            return
        self._t += seconds


class AsyncPartialSleepClock:
    def __init__(self) -> None:
        self._t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self._t

    def sleep(self, seconds: float) -> None:
        raise AssertionError("async limiter must not call sync sleep")

    async def asleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if len(self.sleeps) == 1:
            self._t += seconds / 2.0
            return
        self._t += seconds


def test_fake_clock_advance_rejects_negative_seconds() -> None:
    clk = FakeClock()
    clk.advance(2.0)

    with pytest.raises(ValueError):
        clk.advance(-1.0)

    assert clk.now() == 2.0


def test_ratelimit_docstring_describes_proactive_limiter_only() -> None:
    assert ratelimit.__doc__ is not None
    assert "proactive" in ratelimit.__doc__.lower()
    assert "reactive backoff" not in ratelimit.__doc__.lower()


def test_system_clock_sync_and_async_sleep_delegate_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_sleeps: list[float] = []
    async_sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sync_sleeps.append(seconds)

    async def fake_async_sleep(seconds: float) -> None:
        async_sleeps.append(seconds)

    monkeypatch.setattr("stonepy._core.clock.time.sleep", fake_sleep)
    monkeypatch.setattr("stonepy._core.clock.asyncio.sleep", fake_async_sleep)

    clock = SystemClock()
    clock.sleep(0.5)
    asyncio.run(clock.asleep(0.75))

    assert sync_sleeps == [0.5]
    assert async_sleeps == [0.75]


def test_fake_clock_async_sleep_advances_time() -> None:
    clk = FakeClock()

    asyncio.run(clk.asleep(1.5))

    assert clk.now() == 1.5


def test_limiter_sleeps_when_window_full() -> None:
    clk = FakeClock()
    lim = SlidingWindowLimiter(max_requests=2, window_seconds=5.0, clock=clk)
    lim.acquire()
    lim.acquire()
    lim.acquire()
    assert clk.now() >= 5.0


def test_limiter_rejects_invalid_constructor_args() -> None:
    clk = FakeClock()
    invalid_args = (
        (0, 5.0),
        (-1, 5.0),
        (1, 0.0),
        (1, -1.0),
    )

    for max_requests, window_seconds in invalid_args:
        with pytest.raises(ValueError):
            SlidingWindowLimiter(
                max_requests=max_requests,
                window_seconds=window_seconds,
                clock=clk,
            )


def test_limiter_evicts_events_at_exact_window_boundary() -> None:
    clk = FakeClock()
    lim = SlidingWindowLimiter(max_requests=2, window_seconds=5.0, clock=clk)
    lim.acquire()
    lim.acquire()

    clk.advance(5.0)
    lim.acquire()

    assert clk.now() == 5.0


def test_limiter_waits_until_slot_is_actually_free() -> None:
    clk = PartialSleepClock()
    lim = SlidingWindowLimiter(max_requests=1, window_seconds=4.0, clock=clk)
    lim.acquire()

    lim.acquire()

    assert clk.now() == 4.0
    assert clk.sleeps == [4.0, 2.0]


def test_async_limiter_waits_until_slot_is_actually_free() -> None:
    clk = AsyncPartialSleepClock()
    lim = SlidingWindowLimiter(max_requests=1, window_seconds=4.0, clock=clk)

    async def run() -> None:
        await lim.aacquire()
        await lim.aacquire()

    asyncio.run(run())

    assert clk.now() == 4.0
    assert clk.sleeps == [4.0, 2.0]


def test_backoff_prefers_retry_after() -> None:
    assert backoff_delay(1, retry_after=2.0, jitter=0.0) == 2.0


def test_backoff_clamps_retry_after_to_cap() -> None:
    assert backoff_delay(1, retry_after=120.0, cap=30.0, jitter=0.0) == 30.0


def test_backoff_requires_jitter_keyword_argument() -> None:
    jitter = inspect.signature(backoff_delay).parameters["jitter"]

    assert jitter.kind is inspect.Parameter.KEYWORD_ONLY
    assert jitter.default is inspect.Parameter.empty


def test_backoff_is_exponential_with_jitter_cap() -> None:
    assert backoff_delay(1, None, base=1.0, cap=30.0, jitter=1.0) == 2.0
    assert backoff_delay(10, None, base=1.0, cap=30.0, jitter=1.0) == 30.0
    assert backoff_delay(2, None, base=1.0, cap=30.0, jitter=0.0) == 2.0


class _ThreadedFakeClock:
    """FakeClock twin whose state is guarded for cross-thread use in these tests."""

    def __init__(self) -> None:
        self._t = 0.0
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self._t += max(0.0, seconds)


def _run_threads(worker: Callable[[], None], count: int) -> list[BaseException]:
    barrier = threading.Barrier(count)
    errors: list[BaseException] = []

    def wrapped() -> None:
        try:
            barrier.wait()
            worker()
        except BaseException as exc:  # noqa: BLE001 - captured for the assertion
            errors.append(exc)

    threads = [threading.Thread(target=wrapped) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)
    return errors


def test_sliding_window_never_over_admits_across_threads() -> None:
    clock = _ThreadedFakeClock()
    limiter = SlidingWindowLimiter(4, 60.0, clock)

    errors = _run_threads(limiter.acquire, 8)

    assert not errors
    admitted_in_first_window = [t for t in limiter._events if t < 60.0]
    assert len(admitted_in_first_window) <= 4


def test_bucketed_limiter_concurrent_bucket_creation_loses_no_grants() -> None:
    clock = _ThreadedFakeClock()
    limiter = BucketedSlidingWindowLimiter(1000, 60.0, clock)

    errors = _run_threads(lambda: limiter.acquire("order"), 8)

    assert not errors
    assert len(limiter._limiters) == 1
    assert len(limiter._limiters["order"]._events) == 8
