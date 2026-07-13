"""Best-effort proactive sliding-window limiter; reactive sleeps are per-call pipeline backoff."""

from __future__ import annotations

import threading
from collections import deque

from stonepy._core.clock import AsyncClock, Clock


class SlidingWindowLimiter:
    """Allow at most ``max_requests`` acquisitions within any ``window_seconds`` window.

    Records the timestamp of each grant and, when the window is full, sleeps until the oldest
    grant ages out. ``max_requests`` and ``window_seconds`` must both be positive.
    Safe for concurrent use from multiple threads; the lock is never held while sleeping.
    """

    def __init__(self, max_requests: int, window_seconds: float, clock: Clock) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._events: deque[float] = deque()
        self._state_lock = threading.Lock()

    def acquire(self) -> None:
        """Acquire one slot, sleeping until the window has room if it is currently full."""
        while True:
            with self._state_lock:
                now = self._clock.now()
                self._evict(now)
                if len(self._events) < self._max:
                    self._events.append(now)
                    return
                wait = self._events[0] + self._window - now
            self._clock.sleep(max(0.0, wait))

    async def aacquire(self) -> None:
        """Acquire one slot, awaiting until the window has room if it is currently full."""
        while True:
            with self._state_lock:
                now = self._clock.now()
                self._evict(now)
                if len(self._events) < self._max:
                    self._events.append(now)
                    return
                wait = self._events[0] + self._window - now
            await self._asleep(max(0.0, wait))

    def _evict(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] <= cutoff:
            self._events.popleft()

    async def _asleep(self, seconds: float) -> None:
        if isinstance(self._clock, AsyncClock):
            await self._clock.asleep(seconds)
            return
        self._clock.sleep(seconds)


class BucketedSlidingWindowLimiter:
    """Bucket-compatible facade over one shared sliding-window limiter.

    Generated endpoint specs still supply resource-group bucket names, but CIAPI documents one
    aggregate server budget. All bucket names therefore acquire from the same window. The shared
    limiter is created lazily under a lock, and that lock is never held while sleeping or awaiting.
    """

    def __init__(self, max_requests: int, window_seconds: float, clock: Clock) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._shared_limiter: SlidingWindowLimiter | None = None
        self._limiter_lock = threading.Lock()

    def acquire(self, bucket: str) -> None:
        """Acquire one slot from the aggregate window shared by every *bucket*."""
        self._limiter(bucket).acquire()

    async def aacquire(self, bucket: str) -> None:
        """Await one slot from the aggregate window shared by every *bucket*."""
        await self._limiter(bucket).aacquire()

    def _limiter(self, _bucket: str) -> SlidingWindowLimiter:
        with self._limiter_lock:
            limiter = self._shared_limiter
            if limiter is None:
                limiter = SlidingWindowLimiter(
                    max_requests=self._max_requests,
                    window_seconds=self._window_seconds,
                    clock=self._clock,
                )
                self._shared_limiter = limiter
            return limiter


def backoff_delay(
    attempt: int,
    retry_after: float | None,
    *,
    base: float = 1.0,
    cap: float = 30.0,
    jitter: float,
) -> float:
    """Return the delay before the next retry, in seconds.

    Honors a server ``retry_after`` when supplied (clamped to ``cap``); otherwise applies
    capped exponential backoff (``base * 2**attempt``) scaled by *jitter* in ``[0, 1]`` to
    spread retries across ``[50%, 100%]`` of the computed delay.
    """
    if retry_after is not None:
        return min(cap, max(0.0, retry_after))
    raw = min(cap, base * float(2**attempt))
    bounded_jitter = min(1.0, max(0.0, jitter))
    return raw * (0.5 + bounded_jitter * 0.5)
