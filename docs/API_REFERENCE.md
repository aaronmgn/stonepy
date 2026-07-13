# API Reference

`stonepy` is a typed Python client for the StoneX (CIAPI) v2 trading API, providing both
synchronous and asynchronous clients generated from the upstream API catalog.

- **Package:** [`stonepy` on PyPI](https://pypi.org/project/stonepy/)
- **Upstream API documentation:** <https://docs.labs.gaincapital.com/> - the authoritative
  CIAPI v2 contract (HTTP Services and Data Types). Every generated endpoint records its
  originating documentation page as a `source_url`.

## Installation

```bash
pip install stonepy
```

## Public Surface

The top-level `stonepy` package exports the client entry points and the error hierarchy:

| Export | Description |
| --- | --- |
| `ClientConfig` | Connection, credential, timeout, retry, and rate-limit configuration. Build it directly or via `ClientConfig.from_env()`. |
| `StoneXClient` | Synchronous client; use as a context manager (`with StoneXClient(config) as client:`). |
| `AsyncStoneXClient` | Asynchronous client; use as `async with AsyncStoneXClient(config) as client:`. |
| `StoneXError` | Base class for every exception raised by the library. |

### Error Hierarchy

All exceptions inherit from `StoneXError`:

- `AuthenticationError` - log-on failed or the session could not be refreshed.
- `RateLimitError` - the API returned a rate-limit response; inspect `retry_after`.
- `OrderRejectedError` - the request was accepted but the order was rejected.
- `StoneXAPIError` - a non-success API response; exposes `http_status`, `error_code`, and `error_message`.
- `ResponseParseError` - the response body did not match the expected schema.
- `TransportError` - the request never completed (connection or timeout error).

## Resource Groups

Resource groups are exposed as properties on both clients and mirror the StoneX API surface:

`cfd`, `client_preference`, `clientapplication`, `clientpreference`, `fixedmargin`, `margin`,
`market`, `message`, `news`, `order`, `order_including_closed`, `pm`, `preference`,
`price_alert`, `session`, `spread`, `tradingadvisor`, `user_account`, and `watchlist`.

Each method maps to a single CIAPI v2 endpoint:

```python
session = client.session.log_on(request_dto)
page = client.market.list_market_search_paginated("gold", ...)
```

`client.order.place_order(...)` is the clearer alias for the generated `client.order.order(...)`
call; both remain available.

## Models and DTOs

Request and response models are exported from `stonepy.models`:

- Request DTO names usually end in `RequestDTO`
  (e.g. `NewTradeOrderRequestDTO`, `NewStopLimitOrderRequestDTO`, `CancelOrderRequestDTO`).
- Response DTO names usually end in `ResponseDTO`.

Models are [Pydantic](https://docs.pydantic.dev/) models: they validate input and serialise to
the JSON shapes the API expects.

## Authentication and Sessions

See the [Authentication & sessions guide](guide/authentication.md) for the full authentication
flow and automatic session-refresh behaviour.

## Authoritative Contract

For endpoint semantics, request bodies, and response bodies, the upstream
[StoneX CIAPI v2 documentation](https://docs.labs.gaincapital.com/) remains authoritative.
`stonepy` tracks that contract through its generated catalog; the pinned catalog revision is
recorded in [`CATALOG_VERSION`](https://github.com/aaronmgn/stonepy/blob/main/CATALOG_VERSION).
