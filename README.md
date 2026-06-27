# stonepy

[![PyPI version](https://img.shields.io/pypi/v/stonepy.svg)](https://pypi.org/project/stonepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/stonepy.svg)](https://pypi.org/project/stonepy/)
[![CI](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml/badge.svg)](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://aaronmgn.github.io/stonepy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/aaronmgn/stonepy/blob/main/LICENSE)

Python client for the StoneX (CIAPI) v2 trading API.

📖 **Documentation:** <https://aaronmgn.github.io/stonepy/>

## Installation

```bash
pip install stonepy
```

Requires Python >= 3.11.

## Quickstart

```python
from stonepy import ClientConfig, StoneXClient
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

with StoneXClient(config) as client:
    session = client.session.log_on(
        ApiLogOnRequestDTO(
            UserName="username",
            Password="password",
            AppKey="app-key",
            AppVersion="stonepy",
            AppComments="",
        )
    )
    print(session.status_code)
```

Environment-based configuration is also available:

```python
from stonepy import ClientConfig, StoneXClient

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    print(client.session)
```

`ClientConfig.from_env()` reads `STONEX_BASE_URL`, `STONEX_APP_KEY`, `STONEX_USERNAME`,
and `STONEX_PASSWORD`. `STONEX_BASE_URL` is required unless `base_url=` is passed.

## Authentication and Sessions

Calling `client.session.log_on(...)` establishes the authenticated session token that the
client attaches to every subsequent request. The token is held by the client for the life of
its context manager.

If you supply `app_key`, `username`, and `password` on `ClientConfig` (directly or via
`ClientConfig.from_env()`), the client also refreshes the session automatically: it
re-authenticates in the background before the token expires, controlled by
`ClientConfig.proactive_refresh_seconds` (default `1080.0`, i.e. 18 minutes), and transparently
re-logs-on if a request is rejected with an expired-session error. Without those credentials you
must call `log_on` yourself and manage re-authentication.

```python
config = ClientConfig(
    base_url="https://ciapi.cityindex.com/TradingAPI",
    app_key="app-key",
    username="username",
    password="password",
)  # credentials present -> automatic proactive session refresh
```

## Async Usage

```python
from stonepy import AsyncStoneXClient, ClientConfig
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

async with AsyncStoneXClient(config) as client:
    session = await client.session.log_on(
        ApiLogOnRequestDTO(
            UserName="username",
            Password="password",
            AppKey="app-key",
            AppVersion="stonepy",
            AppComments="",
        )
    )
    print(session.status_code)
```

Use `aclose()` for async clients when not using `async with`; use `close()` for sync clients.

## Error Handling

All library exceptions inherit from `StoneXError`.

```python
from stonepy import RateLimitError, StoneXAPIError, StoneXError, StoneXClient

try:
    with StoneXClient(config) as client:
        client.order.list_active_orders(request_dto)
except RateLimitError as exc:
    print(exc.retry_after)
except StoneXAPIError as exc:
    print(exc.http_status, exc.error_code, exc.error_message)
except StoneXError as exc:
    print(exc)
```

Important subclasses include `AuthenticationError`, `RateLimitError`,
`OrderRejectedError`, `ResponseParseError`, `StoneXAPIError`, and `TransportError`.

## Pagination

Paginated API methods return the page DTO documented by StoneX. For example,
`client.market.list_market_search_paginated(...)` accepts `page`, `page_size`, and
`order_by` keyword arguments and returns `ListMarketSearchPaginatedResponseDTO`:

```python
page = client.market.list_market_search_paginated(
    "gold",
    search_by_market_code=False,
    search_by_market_name=True,
    spread_product_type=True,
    cfd_product_type=True,
    binary_product_type=False,
    ascending_order=True,
    include_options=False,
    client_account_id=12345,
    page=0,
    page_size=100,
)
print(page.total_number_of_results)
```

## API Reference

See `docs/API_REFERENCE.md` for the public package surface and links to the upstream StoneX
CIAPI v2 documentation.

## Development

```bash
uv venv
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor guide.

## AI Use Disclaimer

Portions of this project, including the generated API bindings, DTO models, and documentation,
were produced with the assistance of AI tooling and reviewed by a human maintainer. The library
is tested against the StoneX CIAPI v2 contract but is provided "as is", without warranty of any
kind (see [LICENSE](LICENSE)).

`stonepy` is **unofficial** and is not affiliated with, endorsed by, or supported by StoneX,
City Index, or GAIN Capital. Trading carries financial risk; validate all behaviour against the
[official API documentation](https://docs.labs.gaincapital.com/) before using it with a live
account.
