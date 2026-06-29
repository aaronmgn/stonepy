# Testing with stonepy

This guide shows how to mock `stonepy` in your own test suite so you can exercise
code that calls the StoneX / City Index API without hitting the live service. It
uses [`respx`](https://lundberg.github.io/respx/), the same mocking library
`stonepy` uses internally, so the patterns here mirror the project's own tests.

## How stonepy builds its HTTP client

`stonepy` does all I/O through a thin transport layer (`SyncTransport` /
`AsyncTransport` in `stonepy._core.transport`). When you construct a client from a
`ClientConfig`, the transport builds a standard `httpx` client whose `base_url` is
your configured `base_url`:

```python
# stonepy/_core/transport.py (SyncTransport.__init__, abridged)
self._client = httpx.Client(
    base_url=base_url.base_url,
    verify=base_url.verify_tls,
    proxy=base_url.proxy,
    timeout=httpx.Timeout(...),
    limits=httpx.Limits(max_connections=base_url.max_connections),
)
```

The async client is built the same way with `httpx.AsyncClient`. Requests are sent
via `self._client.request(method, url, headers=..., params=..., content=...)`.

This matters for testing in two ways:

- Because `stonepy` uses a real `httpx` client under the hood, `respx` can
  intercept its requests at the transport level. You do not need to monkeypatch
  any `stonepy` internals.
- `respx` matches on the **full absolute URL**. The URL `stonepy` sends is your
  `base_url` joined with each endpoint's path (for example
  `https://ciapi.cityindex.com/TradingAPI` + `/order/openpositions`). A few v2
  endpoints (such as `log_on`) are served from the host root instead, so their
  URL drops the base path (`https://ciapi.cityindex.com` + `/v2/session`).
  Register your mock routes against that full URL.

!!! tip
    Pick a `base_url` in your tests and reuse it for every mocked route. Any
    valid URL works since nothing is actually sent over the network. The examples
    below use the real CIAPI base URL so the paths read realistically, but
    something like `https://api.example` is equally fine (and is what the
    `stonepy` test suite itself uses).

## Installing respx

`respx` is already a dev dependency of `stonepy`. In your own project add it
alongside `pytest`:

```bash
pip install respx pytest
```

## A complete, runnable example

The example below mocks two endpoints, `log_on` and `get_market_information`, then
asserts that the client parses the JSON responses into the generated Pydantic
DTOs. Save it as `test_stonepy_mock.py` and run it with `pytest`.

A few things to know before reading it:

- `log_on` issues a `POST` to `{host}/v2/session` (the host root, not under the
  `base_url` path) and returns an
  `ApiLogOnResponseDTOv2`. On success `stonepy` stores the returned session token
  and automatically attaches it as a `Session` header on every later request, so
  your data-call assertions can check for it.
- `get_market_information(market_id, client_account_id)` issues a `GET` to
  `{base_url}/market/v2/market/{market_id}/information` with
  `clientAccountId` as a query parameter, and returns a
  `GetMarketInformationResponseDTO`.
- Both clients are context managers, so `with StoneXClient(...) as client:`
  closes the underlying `httpx` client for you.

```python
import asyncio
import json

import httpx
import respx

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy.models import (
    ApiLogOnRequestDTO,
    ApiLogOnResponseDTOv2,
    GetMarketInformationResponseDTO,
)

BASE_URL = "https://ciapi.cityindex.com/TradingAPI"

# A minimal but valid LogOn response body. Field names are the API's PascalCase
# wire names; stonepy maps them to snake_case attributes on the DTO.
LOGON_BODY = {
    "Session": "TEST-SESSION-TOKEN",
    "PasswordChangeRequired": False,
    "AllowedAccountOperator": False,
    "StatusCode": 1,
    "Is2FAEnabled": False,
    "TwoFAToken": "",
    "Additional2FAMethods": [],
}

# Optional DTO fields can be omitted; supply only what your test asserts on.
MARKET_BODY = {
    "MarketInformation": {
        "MarketId": 1,
        "Name": "UK 100",
    }
}


@respx.mock
def test_sync_flow() -> None:
    logon_route = respx.post("https://ciapi.cityindex.com/v2/session").mock(
        return_value=httpx.Response(200, json=LOGON_BODY)
    )
    market_route = respx.get(
        f"{BASE_URL}/market/v2/market/99498/information"
    ).mock(return_value=httpx.Response(200, json=MARKET_BODY))

    config = ClientConfig(base_url=BASE_URL)
    with StoneXClient(config) as client:
        logon = client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="me",
                Password="secret",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
        # The response is parsed into a typed DTO.
        assert isinstance(logon, ApiLogOnResponseDTOv2)
        assert logon.session == "TEST-SESSION-TOKEN"

        market = client.market.get_market_information("99498", 12345)
        assert isinstance(market, GetMarketInformationResponseDTO)
        assert market.market_information.name == "UK 100"

    # Assert on what stonepy actually sent.
    assert logon_route.called
    assert json.loads(logon_route.calls[0].request.content)["UserName"] == "me"
    # The session token from log_on is attached automatically.
    assert market_route.calls[0].request.headers["Session"] == "TEST-SESSION-TOKEN"
    assert dict(market_route.calls[0].request.url.params) == {"clientAccountId": "12345"}
```

### Testing the async client

The async client is mocked identically. `respx.mock` patches `httpx` for both sync
and async transports in the same way, so the only differences are
`AsyncStoneXClient`, `async with`, and `await` on the calls. Drive the coroutine
with `asyncio.run` (the `stonepy` suite uses this style; if you prefer, install
`pytest-asyncio` and mark the test instead).

```python
@respx.mock
def test_async_flow() -> None:
    respx.post("https://ciapi.cityindex.com/v2/session").mock(
        return_value=httpx.Response(200, json=LOGON_BODY)
    )
    market_route = respx.get(
        f"{BASE_URL}/market/v2/market/99498/information"
    ).mock(return_value=httpx.Response(200, json=MARKET_BODY))

    async def run() -> None:
        config = ClientConfig(base_url=BASE_URL)
        async with AsyncStoneXClient(config) as client:
            logon = await client.session.log_on(
                ApiLogOnRequestDTO(
                    UserName="me",
                    Password="secret",
                    AppKey="app-key",
                    AppVersion="stonepy",
                    AppComments="",
                )
            )
            assert isinstance(logon, ApiLogOnResponseDTOv2)

            market = await client.market.get_market_information("99498", 12345)
            assert isinstance(market, GetMarketInformationResponseDTO)
            assert market.market_information.name == "UK 100"

    asyncio.run(run())
    assert market_route.called
```

## Mocking without log_on

If the code under test only exercises a single data call, you can mock just that
one endpoint. You still need a session token in place so `stonepy` attaches the
`Session` header. The simplest approach is to mock `log_on` and call it, exactly
as above. The `stonepy` test suite seeds the token directly via the internal
`client._ctx.session.set_token(...)` (async: `aset_token`), but that touches a
private attribute and may change between releases. Prefer mocking and calling
`log_on` in adopter tests so you depend only on the public API.

## Asserting on requests

`respx` records every matched call. Useful assertions:

- `route.called` / `route.call_count` to confirm an endpoint was hit.
- `route.calls[0].request.method` and `route.calls[0].request.url.path`.
- `dict(route.calls[0].request.url.params)` for query parameters. Note that
  `stonepy` serializes all query values to strings (for example `12345` becomes
  `"12345"`, and booleans become `"true"` / `"false"`).
- `route.calls[0].request.headers["Session"]` to confirm the session token was
  attached to authenticated calls.
- `json.loads(route.calls[0].request.content)` for the request body of POST/PUT
  endpoints.

## Simulating error responses

To exercise your error handling, return a non-2xx response. `stonepy` decodes API
error envelopes into its typed exceptions (`AuthenticationError`,
`RateLimitError`, `OrderRejectedError`, `StoneXAPIError`, and so on), so you can
assert your code reacts correctly:

```python
import pytest

import respx
import httpx

from stonepy import AuthenticationError, ClientConfig, StoneXClient
from stonepy.models import ApiLogOnRequestDTO

BASE_URL = "https://ciapi.cityindex.com/TradingAPI"


@respx.mock
def test_logon_failure_raises() -> None:
    respx.post("https://ciapi.cityindex.com/v2/session").mock(
        return_value=httpx.Response(
            401,
            json={"ErrorCode": 4011, "ErrorMessage": "bad credentials", "HttpStatus": 401},
        )
    )

    with StoneXClient(ClientConfig(base_url=BASE_URL)) as client:
        with pytest.raises(AuthenticationError):
            client.session.log_on(
                ApiLogOnRequestDTO(
                    UserName="me",
                    Password="wrong",
                    AppKey="app-key",
                    AppVersion="stonepy",
                    AppComments="",
                )
            )
```

!!! note
    `stonepy` retries idempotent requests and can transparently re-authenticate on
    a `401` when credentials are configured. If a single mocked response is not
    enough, use `respx`'s `side_effect=[...]` to queue a sequence of responses
    (for example a `401` followed by a `200`) so each retry receives the next one.

!!! warning
    Endpoints that place or cancel live orders (for example
    `client.order.place_order` and `client.order.cancel_order`) execute real
    trades against a live account. Keep them behind mocked routes in your test
    suite. With `respx` active, the request is intercepted and never reaches the
    exchange, so it is safe to assert on the request body and return a canned
    response.
