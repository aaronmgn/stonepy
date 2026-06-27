# Resilience: timeouts, retries, and rate limiting

Every `StoneXClient` and `AsyncStoneXClient` is built from a `ClientConfig`. The resilience-related fields on that config control three independent layers:

1. **Timeouts and connection pooling** - how long a single HTTP attempt may take and how many sockets are kept open.
2. **Retries** - which failed attempts are transparently re-sent, with what backoff, and for how long in total.
3. **Rate limiting** - a proactive client-side sliding-window limiter, plus reactive handling of server-side `429` responses.

All three are tuned the same way: construct a `ClientConfig` with the fields you want and pass it to the client. Every field shown below has a default, so you only override what you need.

```python
from stonepy import ClientConfig, StoneXClient

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    app_key="your-app-key",
    username="your-username",
    password="your-password",
)
client = StoneXClient(config)
```

---

## 1. Timeouts and connection pooling

`ClientConfig` exposes four separate timeouts, each mapped onto an `httpx.Timeout`, plus a connection-pool size mapped onto `httpx.Limits`. These are wired up in `SyncTransport` / `AsyncTransport` (`src/stonepy/_core/transport.py`).

| `ClientConfig` field | Default | httpx target | Meaning |
| --- | --- | --- | --- |
| `connect_timeout` | `10.0` | `httpx.Timeout(connect=...)` | Max seconds to establish a TCP/TLS connection. |
| `read_timeout` | `30.0` | `httpx.Timeout(read=...)` | Max seconds to wait for a chunk of the response body. Also used as the httpx default timeout. |
| `write_timeout` | `30.0` | `httpx.Timeout(write=...)` | Max seconds to send a chunk of the request body. |
| `pool_timeout` | `5.0` | `httpx.Timeout(pool=...)` | Max seconds to wait for a free connection from the pool. |
| `max_connections` | `20` | `httpx.Limits(max_connections=...)` | Maximum number of simultaneous connections. |

The transport constructs the underlying client like this (from `transport.py`):

```python
import httpx

# Illustrative - this is what the transport does internally.
httpx.Client(
    base_url=config.base_url,
    verify=config.verify_tls,
    proxy=config.proxy,
    timeout=httpx.Timeout(
        config.read_timeout,            # default timeout
        connect=config.connect_timeout,
        read=config.read_timeout,
        write=config.write_timeout,
        pool=config.pool_timeout,
    ),
    limits=httpx.Limits(max_connections=config.max_connections),
)
```

!!! note
    Each timeout governs a single HTTP attempt, not the whole call. When retries are enabled, a slow endpoint can take up to `read_timeout` per attempt, and the total wall-clock time is bounded separately by `retry_budget_seconds` (see below).

Tuning example - shorter connect and read budgets, more concurrency for an async fan-out:

```python
from stonepy import ClientConfig

config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    connect_timeout=5.0,
    read_timeout=15.0,
    write_timeout=15.0,
    pool_timeout=2.0,
    max_connections=50,
)
```

!!! tip
    If you see `TransportError` mentioning the pool, your `max_connections` is too low for your concurrency level (or requests are not completing). Raise `max_connections` or lower concurrency.

---

## 2. Retries

Retry behavior is driven by two `ClientConfig` fields and implemented in `RetryPolicy` (`src/stonepy/_core/retry.py`), `backoff_delay` (`src/stonepy/_core/ratelimit.py`), and the request loop in `CallContext.invoke` / `ainvoke` (`src/stonepy/_core/pipeline.py`).

| `ClientConfig` field | Default | Meaning |
| --- | --- | --- |
| `max_retries` | `3` | Maximum number of retry attempts. The attempt counter starts at `0`; a retry is allowed only while `attempt < max_retries`. |
| `retry_budget_seconds` | `30.0` | Hard cap on total wall-clock time (including the upcoming sleep) measured from the start of the call. |

### Which failures are retried

`RetryPolicy.should_retry` decides, and the rules are deliberately conservative:

- **Attempt cap.** If `attempt >= max_retries`, never retry.
- **Idempotency gate.** If the endpoint is **not** idempotent, never auto-retry. This is a trade-safety guarantee: non-idempotent calls (for example placing or cancelling orders) are never re-sent automatically, so they cannot be double-submitted.
- **Transport errors** (connect/read failures where no response was received): retried only if the endpoint is idempotent.
- **Server errors with a response**: retried only for HTTP status `502`, `503`, or `504` (`_RETRYABLE_STATUS`), and only for idempotent endpoints.
- All other 4xx/5xx responses are **not** retried - they are mapped straight to an exception.

`429` responses are handled by a separate path (see rate limiting below) via `should_retry_rate_limit`, which also requires `attempt < max_retries` and an idempotent endpoint.

!!! warning
    Order placement and cancellation are non-idempotent and are therefore **never** retried automatically, even on a transport error where it is unknown whether the server received the request. If such a call raises, you must decide whether to re-send it yourself after checking order state.

### Backoff and jitter

The delay before each retry comes from `backoff_delay(attempt, retry_after, *, base=1.0, cap=30.0, jitter=...)`:

- **If a `Retry-After` value is present** (parsed from the response header): the delay is `min(30.0, max(0.0, retry_after))` - the server's hint, clamped to `[0, 30]` seconds. Jitter is not applied in this case.
- **Otherwise** (exponential backoff with jitter):
  - `raw = min(30.0, 1.0 * 2 ** attempt)` - exponential growth capped at 30 seconds.
  - the returned delay is `raw * (0.5 + jitter * 0.5)` where `jitter` is a random float in `[0, 1)`.
  - Net effect: the actual sleep is a random value between **50% and 100%** of `raw`.

Because `attempt` starts at `0`, the (un-jittered) `raw` progression is `1s, 2s, 4s, 8s, ...` capped at `30s`. So the first retry waits roughly 0.5-1.0s, the second roughly 1-2s, the third roughly 2-4s.

### How the budget caps total retry time

Before sleeping for a retry, the pipeline checks `_within_retry_budget(started_at, delay)`:

```python
# From pipeline.py
def _within_retry_budget(self, started_at, delay):
    return (self.clock.now() + delay - started_at) <= self.config.retry_budget_seconds
```

`started_at` is captured once at the very beginning of the call. The check includes the **upcoming** `delay`, so a retry is skipped if sleeping for it would push the elapsed time past `retry_budget_seconds`. When the budget is exhausted (or `max_retries` is reached, or the endpoint is non-idempotent), the loop stops retrying and raises the mapped error instead.

So a call stops retrying as soon as **either** limit is hit: the attempt count (`max_retries`) **or** the time budget (`retry_budget_seconds`).

!!! note
    The retry budget does not abort an in-flight HTTP attempt; per-attempt duration is still governed by the timeouts. The budget only prevents starting a *new* retry sleep that would exceed it.

### Tuning retries

```python
from stonepy import ClientConfig

# More aggressive: up to 5 retries within a 60s total budget.
config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    max_retries=5,
    retry_budget_seconds=60.0,
)

# Disable automatic retries entirely.
no_retry = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    max_retries=0,
)
```

With `max_retries=0`, `should_retry` returns `False` on the first attempt (`0 >= 0`), so every failure surfaces immediately.

---

## 3. Rate limiting

There are two distinct mechanisms, both controlled from `ClientConfig`.

### Client-side proactive limiter (sliding window)

The clients use a `BucketedSlidingWindowLimiter` (`src/stonepy/_core/ratelimit.py`), constructed from these fields:

| `ClientConfig` field | Default | Meaning |
| --- | --- | --- |
| `rate_limit_max` | `500` | Maximum requests allowed per window, **per bucket**. |
| `rate_limit_window_seconds` | `5.0` | Length of the sliding window in seconds. |

How it works:

- Requests are partitioned into **buckets** by `spec.rate_limit_bucket` (a fixed label baked into each generated `EndpointSpec`, for example `"order"`). Each bucket gets its own independent `SlidingWindowLimiter` with the same `rate_limit_max` and `rate_limit_window_seconds`. The limit is therefore applied **per bucket**, not globally across all endpoints.
- Before every send, the pipeline calls `acquire(bucket)`. The limiter keeps a deque of recent request timestamps, evicts any older than `window_seconds`, and:
  - if fewer than `rate_limit_max` events remain in the window, it records "now" and returns immediately;
  - otherwise it sleeps until the oldest in-window event ages out (`oldest + window - now`), then re-checks.

This is a true sliding window (not a fixed bucket reset), so it smooths bursts rather than allowing a full burst at every window boundary. It is best-effort and local to the process - it does not coordinate across multiple client instances or machines.

### Server-side 429 handling

Even with the proactive limiter, the server may still return HTTP `429`. The pipeline detects this (`_is_rate_limited` treats any `429` as rate-limited) and:

1. Parses the `Retry-After` header via `_parse_retry_after`. This accepts either a numeric seconds value or an HTTP-date, and returns the delay in seconds (clamped to `>= 0`), or `None` if absent/unparseable.
2. Computes `delay = backoff_delay(attempt, retry_after)` - so a present `Retry-After` is honored directly (clamped to 30s), otherwise exponential-with-jitter is used.
3. Retries only if `_can_retry_rate_limit` passes: the endpoint is idempotent, `attempt < max_retries`, **and** the sleep fits within `retry_budget_seconds`.
4. If it cannot retry (non-idempotent, attempts exhausted, or budget exceeded), it raises `RateLimitError`.

`RateLimitError` carries the parsed value on its `retry_after` attribute (`float | None`), so callers can back off intelligently:

```python
from stonepy import ClientConfig, StoneXClient, RateLimitError

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")
client = StoneXClient(config)

try:
    market = client.market.get_market_information(
        market_id="154297",
        client_account_id=400000000,
    )
except RateLimitError as exc:
    wait_seconds = exc.retry_after if exc.retry_after is not None else 5.0
    print(f"Rate limited; server suggests waiting {wait_seconds}s")
```

!!! note
    `retry_after` is `None` when the server did not send a parseable `Retry-After` header. Always provide a fallback delay, as shown above.

### Tuning rate limiting

```python
from stonepy import ClientConfig

# Tighter local throttle: at most 100 requests per 2s window, per bucket.
config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    rate_limit_max=100,
    rate_limit_window_seconds=2.0,
)
```

!!! warning
    `rate_limit_max` must be a positive integer and `rate_limit_window_seconds` a positive number; the underlying `SlidingWindowLimiter` raises `ValueError` otherwise.

---

## How the three layers interact

For a single call, the order of events inside the pipeline loop is:

1. Acquire a slot from the client-side limiter for the endpoint's bucket (may sleep proactively).
2. Send one HTTP attempt, bounded by the four timeouts.
3. On a transport error or a retryable status (`502/503/504`), or a `429`, decide whether to retry based on idempotency, `max_retries`, and `retry_budget_seconds`; sleep using the backoff/`Retry-After` delay; then loop.
4. When no retry is possible, raise the mapped error (`TransportError`, `RateLimitError`, `AuthenticationError`, or `StoneXAPIError`).

Each layer is independent: timeouts bound a single attempt, the limiter shapes outgoing request rate per bucket, and the retry budget bounds the total wall-clock time spent retrying across attempts.
