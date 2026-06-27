"""Best-effort proactive sliding-window limiter; reactive sleeps are per-call pipeline backoff."""

from __future__ import annotations

from collections import deque

from stonepy._core.clock import AsyncClock, Clock


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float, clock: Clock) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._events: deque[float] = deque()

    def acquire(self) -> None:
        while True:
            now = self._clock.now()
            self._evict(now)
            if len(self._events) < self._max:
                self._events.append(now)
                return

            wait = self._events[0] + self._window - now
            self._clock.sleep(max(0.0, wait))

    async def aacquire(self) -> None:
        while True:
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
    """Sliding-window limiter partitioned by generated endpoint bucket names.

    Buckets are expected to come from the closed set of generated `EndpointSpec`
    constants, not from user input or other high-cardinality values.
    """

    def __init__(self, max_requests: int, window_seconds: float, clock: Clock) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._limiters: dict[str, SlidingWindowLimiter] = {}

    def acquire(self, bucket: str) -> None:
        self._limiter(bucket).acquire()

    async def aacquire(self, bucket: str) -> None:
        await self._limiter(bucket).aacquire()

    def _limiter(self, bucket: str) -> SlidingWindowLimiter:
        key = bucket or "default"
        limiter = self._limiters.get(key)
        if limiter is None:
            limiter = SlidingWindowLimiter(
                max_requests=self._max_requests,
                window_seconds=self._window_seconds,
                clock=self._clock,
            )
            self._limiters[key] = limiter
        return limiter


def backoff_delay(
    attempt: int,
    retry_after: float | None,
    *,
    base: float = 1.0,
    cap: float = 30.0,
    jitter: float,
) -> float:
    if retry_after is not None:
        return min(cap, max(0.0, retry_after))
    raw = min(cap, base * float(2**attempt))
    bounded_jitter = min(1.0, max(0.0, jitter))
    return raw * (0.5 + bounded_jitter * 0.5)
