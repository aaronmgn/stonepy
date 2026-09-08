# stonepy

[![PyPI version](https://img.shields.io/pypi/v/stonepy.svg)](https://pypi.org/project/stonepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/stonepy.svg)](https://pypi.org/project/stonepy/)
[![CI](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml/badge.svg)](https://github.com/aaronmgn/stonepy/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://aaronmgn.github.io/stonepy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://github.com/aaronmgn/stonepy/blob/main/LICENSE)

Python client for the StoneX (CIAPI) v2 trading API.

📖 **Documentation:** <https://aaronmgn.github.io/stonepy/>

## Features

- **Typed models.** Request and response DTO bodies are
  [Pydantic](https://docs.pydantic.dev/) v2 models; some methods take primitive parameters or
  return bare scalars or lists. The package ships a `py.typed` marker, so editors autocomplete
  fields and type checkers can check your calls. See the
  [constructor typing notes](https://aaronmgn.github.io/stonepy/latest/installation/#type-checking-pep-561)
  for current limitations.
- **Sync and async.** Identical APIs on `StoneXClient` and `AsyncStoneXClient`.
- **Complete coverage.** All 128 endpoints of the frozen catalog revision (`CATALOG_VERSION`)
  across 19 resource groups, using the v2 variant of every endpoint that has one.
- **Batteries included.** Automatic session refresh, configurable retries, client-side rate
  limiting, secret-field omission in configuration and model representations, redaction in
  request representations, and a clear exception hierarchy.

> **Project status:** `stonepy` is pre-1.0 (alpha). The public API may change between minor
> releases until 1.0; pin a version for production use.

When upgrading, migrate shared request DTOs to `Request<Name>` variants, replace entry-point
plugins with explicitly constructed resources, and update deprecated resource names. See the
[release notes](https://aaronmgn.github.io/stonepy/latest/changelog/),
[model guide](https://aaronmgn.github.io/stonepy/latest/api/models/), and
[extensibility guide](https://aaronmgn.github.io/stonepy/latest/guide/extensibility/)
for migration details.

## Installation

```bash
pip install stonepy
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add stonepy
```

Requires Python >= 3.11 and pydantic >= 2.7 (< 3.0), with pydantic >= 2.12 on Python 3.14
and newer. `stonepy` ships type information (PEP 561 `py.typed`) that `mypy` and `pyright`
discover automatically; pyright CI is currently advisory.

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
    print(client.user_account.get_client_and_trading_account())
```

`ClientConfig.from_env()` reads `STONEX_BASE_URL`, `STONEX_APP_KEY`, `STONEX_USERNAME`,
and `STONEX_PASSWORD`. `STONEX_BASE_URL` is required unless `base_url=` is passed.

## Authentication and Sessions

Calling `client.session.log_on(...)` establishes the authenticated session token. The client
attaches the current token to subsequent endpoints that use session authentication. Refresh can
replace the token, and `client.session.delete_session(...)` clears it.

Automatic refresh is enabled either by supplying `app_key`, `username`, and `password` on
`ClientConfig` (directly or via `ClientConfig.from_env()`), or by a successful manual `log_on()`,
which installs a replay refresh callable. Proactive refresh runs inline, immediately before the
request that needs it - synchronously in `StoneXClient` and awaited in `AsyncStoneXClient`, with
no background task - once the stored token reaches `ClientConfig.proactive_refresh_seconds`
(default `1080.0`, i.e. 18 minutes). This threshold is based on token age; no server expiry
timestamp is consulted.

After HTTP `401` or `ErrorCode` `4011` (never `4010`) on an authenticated endpoint, the client
refreshes the session once and replays the request once. This applies to every endpoint,
including non-idempotent order calls, because this authentication rejection means the server did
not process the request. Transport, `5xx`, and `429` retries remain idempotency-gated. If
proactive refresh fails with a stonepy error, the client logs a warning and tries the request
with the existing token so reactive authentication recovery can still run. The `ErrorCode` 4011
envelope is recognised only on non-2xx responses.

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

`StoneXError` is the base of the public runtime error hierarchy. Configuration validation
can also raise builtin `TypeError` or `ValueError` exceptions.

```python
from stonepy import (
    ClientConfig,
    RateLimitError,
    StoneXAPIError,
    StoneXClient,
    StoneXError,
)
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

try:
    with StoneXClient(config) as client:
        client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="username",
                Password="password",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
except RateLimitError as exc:
    print(exc.retry_after)
except StoneXAPIError as exc:
    print(exc.http_status, exc.error_code, exc.error_message)
except StoneXError as exc:
    print(exc)
```

Important subclasses include `AuthenticationError`, `RateLimitError`,
`OrderRejectedError`, `OrderStatusUnknownError`, `ResponseParseError`, `StoneXAPIError`, and
`TransportError`.

Unknown fields in nested request DTOs raise Pydantic `ValidationError` before sending an order.
With the default status checks, an order acknowledgement without a usable status raises
`OrderStatusUnknownError`; verify the order state before resubmitting.

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

Full documentation - the guides and a complete API reference - is published at
<https://aaronmgn.github.io/stonepy/>.

## Development

```bash
uv venv
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor guide and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and the
[changelog](https://aaronmgn.github.io/stonepy/latest/changelog/) for release notes.

## Support

- Questions and bug reports: [GitHub issues](https://github.com/aaronmgn/stonepy/issues).
- Security: please report vulnerabilities privately - see [SECURITY.md](SECURITY.md).

## AI Use Disclaimer

Portions of this project, including the generated API bindings, DTO models, and documentation,
were produced with the assistance of AI tooling and reviewed by a human maintainer. The library
is tested against the StoneX CIAPI v2 contract but is provided "as is", without warranty of any
kind (see [LICENSE](LICENSE)).

`stonepy` is **unofficial** and is not affiliated with, endorsed by, or supported by StoneX,
City Index, or GAIN Capital. Trading carries financial risk; validate all behaviour against the
[official API documentation](https://docs.labs.gaincapital.com/) before using it with a live
account.
