# API Reference

`stonepy` is a typed Python client for the StoneX (CIAPI) v2 trading API, providing both
synchronous and asynchronous clients generated from the upstream API catalog.

- **Package:** [`stonepy` on PyPI](https://pypi.org/project/stonepy/)
- **Upstream API documentation:** <https://docs.labs.gaincapital.com/> - the authoritative
  CIAPI v2 contract (HTTP Services and Data Types).

## Installation

```bash
pip install stonepy
```

## Public Surface

The top-level `stonepy` package exports the client entry points and the error hierarchy:

| Export | Description |
| --- | --- |
| `ClientConfig` | Connection, credential, timeout, retry, and rate-limit configuration. Build it directly or via `ClientConfig.from_env()`. |
| `ClientConfigOverrides` | TypedDict for optional `ClientConfig.from_env()` keyword overrides. |
| `StoneXClient` | Synchronous client; use as a context manager (`with StoneXClient(config) as client:`). |
| `AsyncStoneXClient` | Asynchronous client; use as `async with AsyncStoneXClient(config) as client:`. |
| `StoneXError` | Base class for the public runtime error hierarchy. Configuration and validation can also raise builtin `TypeError` or `ValueError`. |

### Extensions

`stonepy.extensions` exports `BaseResource`, `CallContext`, `EndpointSpec`, `Param`, `AuthPolicy`,
and `StatusDomain`. Construct out-of-tree resources with `MyResource(client.call_context)`;
clients and resources expose read-only `call_context` properties. See the
[extensibility guide](guide/extensibility.md) for a complete example.

### Error Hierarchy

The public runtime exceptions inherit from `StoneXError`:

- `AuthenticationError` - log-on failed or the session could not be refreshed.
- `ConfigurationError` - the client has no credentials configured for session refresh.
- `RateLimitError` - the API returned a rate-limit response; inspect `retry_after`.
- `OrderRejectedError` - the request was accepted but the order was rejected.
- `OrderStatusUnknownError` - a write acknowledgement was indeterminate; verify order state before resubmitting.
- `StoneXAPIError` - a non-success API response; exposes `http_status`, `error_code`, and `error_message`.
- `ResponseParseError` - the response body did not match the expected schema.
- `TransportError` - the request never completed (connection or timeout error).

## Resource Groups

Resource groups are exposed as properties on both clients and mirror the StoneX API surface:

`cfd`, `client_preference`, `client_application`, `clientpreference`, `fixed_margin`, `margin`,
`market`, `message`, `news`, `order`, `pm`, `preference`, `price_alert`, `session`, `spread`,
`trading_advisor`, `user_account`, and `watchlist`.

Deprecated compatibility aliases `clientapplication`, `fixedmargin`, and `tradingadvisor`
emit `DeprecationWarning`; use `client_application`, `fixed_margin`, and `trading_advisor`,
respectively. The `order_including_closed` group is also deprecated; replace
`client.order_including_closed.get_order_including_closed(...)` with
`client.order.get_order_including_closed(...)`.

Each generated method maps to a single CIAPI v2 endpoint. The documented `place_order` alias
below maps to the same endpoint as the generated `order` method:

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
- v2 forms end in `RequestDTOv2` or `ResponseDTOv2`.

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
Contributors regenerating catalog-derived files must either set
`STONEPY_CATALOG=/path/to/stonex_api_docs/Docs/catalog` or pass the same directory with the
generator's `--catalog-root` option. The CLI option takes precedence when both are present.
