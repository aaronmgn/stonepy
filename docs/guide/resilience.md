# Resilience: timeouts, retries, and rate limiting

Every `StoneXClient` and `AsyncStoneXClient` is built from a `ClientConfig`. The resilience-related fields on that config control three independent layers:

1. **Timeouts and connection pooling** - how long a single HTTP attempt may take and how many sockets are kept open.
2. **Retries** - which failed attempts are transparently re-sent, with what backoff, and whether the next retry sleep fits the configured admission budget.
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
        config.read_timeout,  # default timeout
        connect=config.connect_timeout,
        read=config.read_timeout,
        write=config.write_timeout,
        pool=config.pool_timeout,
    ),
    limits=httpx.Limits(max_connections=config.max_connections),
)
```

!!! note
    Each timeout governs a single HTTP attempt, not the whole call. `retry_budget_seconds` only
    gates admission of a new retry sleep. In-flight attempts and proactive rate-limit waits can
    push total elapsed time past that budget.

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
| `retry_budget_seconds` | `30.0` | Pre-sleep admission threshold measured from the start of the call. A retry is skipped when its upcoming sleep would exceed the budget; an in-flight attempt is not aborted. |

### Which failures are retried

`RetryPolicy.should_retry` decides transport and server-error retries, and the rules are
deliberately conservative:

- **Attempt cap.** If `attempt >= max_retries`, never retry.
- **Idempotency gate.** Transport errors and retryable `5xx` responses are retried only for
  idempotent endpoints. Non-idempotent calls are not re-sent through this retry path.
- **Transport errors** (connect/read failures where no response was received): retried only if the endpoint is idempotent.
- **Server errors with a response**: retried only for HTTP status `502`, `503`, or `504` (`_RETRYABLE_STATUS`), and only for idempotent endpoints.
- All other 4xx/5xx responses are **not** retried - they are mapped straight to an exception.

`429` responses are handled by a separate path (see rate limiting below) via `should_retry_rate_limit`, which also requires `attempt < max_retries` and an idempotent endpoint.

### Authentication refresh replay

Reactive authentication recovery is separate from the retry policy above. After HTTP `401` or
`ErrorCode` `4011` (never `4010`) on an authenticated endpoint, the client refreshes the session
once and replays the request once. This applies to every authenticated endpoint regardless of
idempotency, including non-idempotent order placement and cancellation calls, because this
authentication rejection means the server did not process the request. Transport, `5xx`, and
`429` retries remain idempotency-gated.

!!! warning
    Order placement and cancellation are not retried after transport errors, `5xx` responses, or
    `429` responses. They can be replayed once only for the `401`/`4011` authentication recovery
    described above. After a transport error, where it is unknown whether the server received the
    request, check order state before deciding whether to re-send it yourself.

### Backoff and jitter

The delay before each retry comes from `backoff_delay(attempt, retry_after, *, base=1.0, cap=30.0, jitter=...)`:

- **If a `Retry-After` value is present** (parsed from the response header): the delay is `max(0.0, retry_after)` - the authoritative server hint with no 30-second cap. Jitter is not applied in this case.
- **Otherwise** (exponential backoff with jitter):
  - `raw = min(30.0, 1.0 * 2 ** attempt)` - exponential growth capped at 30 seconds.
  - the returned delay is `raw * (0.5 + jitter * 0.5)` where `jitter` is a random float in `[0, 1)`.
  - Net effect: the actual sleep is a random value between **50% and 100%** of `raw`.

Because `attempt` starts at `0`, the (un-jittered) `raw` progression is `1s, 2s, 4s, 8s, ...` capped at `30s`. So the first retry waits roughly 0.5-1.0s, the second roughly 1-2s, the third roughly 2-4s.

### How the budget admits retry sleeps

Before sleeping for a retry, the pipeline checks `_within_retry_budget(started_at, delay)`:

```python
# From pipeline.py
def _within_retry_budget(self, started_at, delay):
    return (self.clock.now() + delay - started_at) <= self.config.retry_budget_seconds
```

`started_at` is captured once at the very beginning of the call. The check includes the
**upcoming** `delay`, so a retry is skipped if sleeping for it would push the elapsed time past
`retry_budget_seconds`. For the idempotency-gated transport, `5xx`, and `429` paths, the loop also
stops retrying when `max_retries` is reached or the endpoint is non-idempotent, and raises the
mapped error instead.

No new retry sleep is admitted after either threshold is hit: the attempt count (`max_retries`)
or the pre-sleep budget (`retry_budget_seconds`). An authoritative server `Retry-After` is not
shortened to fit the budget. If that delay would exceed the remaining budget, the request fails
immediately without sleeping or retrying.

!!! note
    The retry budget does not abort an in-flight HTTP attempt; per-attempt duration is still governed by the timeouts. The budget only prevents starting a *new* retry sleep that would exceed it.

### Tuning retries

```python
from stonepy import ClientConfig

# More aggressive: up to 5 retries whose next sleep fits a 60s admission budget.
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

With `max_retries=0`, ordinary transport, 5xx, and 429 retries are disabled; the one-time
authentication refresh and replay is independent of this count.

---

## 3. Rate limiting

There are two distinct mechanisms, both controlled from `ClientConfig`.

### Client-side proactive limiter (sliding window)

The clients use a `BucketedSlidingWindowLimiter` (`src/stonepy/_core/ratelimit.py`), constructed from these fields:

| `ClientConfig` field | Default | Meaning |
| --- | --- | --- |
| `rate_limit_max` | `500` | Maximum aggregate requests allowed per window across all endpoints. |
| `rate_limit_window_seconds` | `5.0` | Length of the sliding window in seconds. |

How it works:

- CIAPI documents one server-side budget: 500 requests over a 5-second window. Generated `EndpointSpec` objects retain their `rate_limit_bucket` resource-group labels for compatibility, but every label maps to one shared `SlidingWindowLimiter`. The configured limit is therefore aggregate across all endpoints used by a client instance.
- Before every send, the pipeline calls `acquire(bucket)`. The shared limiter keeps a deque of recent request timestamps, evicts any older than `window_seconds`, and:
  - if fewer than `rate_limit_max` events remain in the window, it records "now" and returns immediately;
  - otherwise it sleeps until the oldest in-window event ages out (`oldest + window - now`), then re-checks.

This is a true sliding window (not a fixed bucket reset), so it smooths bursts rather than allowing a full burst at every window boundary. It is best-effort and local to a client instance - it does not coordinate across multiple client instances, processes, or machines.

### Server-side 429 handling

Even with the proactive limiter, the server may still return HTTP `429`. The pipeline detects this (`_is_rate_limited` treats any `429` as rate-limited) and:

1. Parses the `Retry-After` header via `_parse_retry_after`. This accepts either a numeric seconds value or an HTTP-date, and returns the delay in seconds (clamped to `>= 0`), or `None` if absent/unparseable.
2. Computes `delay = backoff_delay(attempt, retry_after)` - so a present `Retry-After` is authoritative and uncapped, otherwise capped exponential-with-jitter is used. The 429 path then floors every computed delay at one second, including explicit zero, a past HTTP-date, and a sub-second value.
3. Retries only if `_can_retry_rate_limit` passes: the endpoint is idempotent, `attempt < max_retries`, **and** the full sleep fits within `retry_budget_seconds`. A longer server delay fails fast without sleeping.
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

# Tighter local throttle: at most 100 aggregate requests per 2s window.
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

1. For an authenticated endpoint, perform an age-based proactive refresh if due, then construct
   the authentication and request headers.
2. Acquire a slot from the client-side aggregate limiter (may sleep proactively).
3. Send one HTTP attempt, bounded by the four timeouts.
4. After the first HTTP `401` or `ErrorCode` `4011` (never `4010`) from an authenticated endpoint,
   refresh once and loop to rebuild headers, reacquire the limiter, and replay the request once.
   This branch applies regardless of endpoint idempotency.
5. On a transport error, retryable status (`502/503/504`), or `429`, decide whether to retry based
   on idempotency, `max_retries`, and the pre-sleep `retry_budget_seconds` check; sleep using the
   backoff/`Retry-After` delay, then loop.
6. When no replay or retry is possible, raise the mapped error (`TransportError`,
   `RateLimitError`, `AuthenticationError`, or `StoneXAPIError`).

Each layer is independent: timeouts bound a single attempt, the limiter shapes aggregate outgoing
request rate, and the retry budget gates new retry sleeps. In-flight attempts and proactive
rate-limit waits can push total elapsed time past the budget.
