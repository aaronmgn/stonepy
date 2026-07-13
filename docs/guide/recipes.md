# Recipes

Short, copy-paste task snippets across the StoneX (CIAPI v2) resource groups. Every
method name, argument, and DTO below is verified against the source. Each snippet defines
its own variables so you can paste and adapt it directly.

All snippets use the synchronous `StoneXClient`. The `AsyncStoneXClient` exposes the same
resource groups and method names with `async`/`await` and `async with`.

!!! note
    Replace `https://example.com/ciapi` and all credential / account / market values with
    your own. The `base_url` points at your CIAPI v2 root.

## Log on and reuse the session

Build a `ClientConfig`, open the client as a context manager, and call
`client.session.log_on(...)` with an `ApiLogOnRequestDTO`. The client stores the returned
session token internally, so every later call on the same client reuses it.

```python
from stonepy import StoneXClient, ClientConfig
from stonepy.models import ApiLogOnRequestDTO

config = ClientConfig(base_url="https://example.com/ciapi")

with StoneXClient(config) as client:
    response = client.session.log_on(
        ApiLogOnRequestDTO(
            user_name="my-username",
            password="my-password",
            app_key="my-app-key",
            app_version="stonepy",
            app_comments="",
        )
    )
    print("session token:", response.session)

    # The token is now reused automatically by subsequent calls on `client`.
    positions = client.order.list_open_positions()
    print("open positions:", len(positions.open_positions or []))
```

To log off explicitly, call `client.session.delete_session(user_name, session)`:

```python
client.session.delete_session("my-username", response.session or "")
```

## Configure automatic session refresh from the environment

If you set credentials on the `ClientConfig` (directly or via `from_env()`), the client logs
on automatically the first time it needs a session and re-logs on when the token nears
expiry. `from_env()` reads `STONEX_BASE_URL`, `STONEX_APP_KEY`, `STONEX_USERNAME`, and
`STONEX_PASSWORD`; `base_url` is required.

```bash
export STONEX_BASE_URL="https://example.com/ciapi"
export STONEX_APP_KEY="my-app-key"
export STONEX_USERNAME="my-username"
export STONEX_PASSWORD="my-password"
```

```python
from stonepy import StoneXClient, ClientConfig

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    # No explicit log_on() call needed - the session is acquired and refreshed for you.
    positions = client.order.list_open_positions()
    print("open positions:", len(positions.open_positions or []))
```

!!! tip
    `from_env()` accepts keyword overrides, e.g.
    `ClientConfig.from_env(proactive_refresh_seconds=600.0)`. Automatic refresh only
    activates when `username`, `password`, and `app_key` are all set.

## Search markets (all 9 required arguments)

`list_market_search_paginated` takes **nine** required positional-or-keyword arguments
before any keyword-only paging options. Omitting one is a common mistake. The required
arguments, in order, are: `query`, `search_by_market_code`, `search_by_market_name`,
`spread_product_type`, `cfd_product_type`, `binary_product_type`, `ascending_order`,
`include_options`, `client_account_id`.

```python
from stonepy import StoneXClient, ClientConfig

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    results = client.market.list_market_search_paginated(
        "GBP/USD",   # query
        True,        # search_by_market_code
        True,        # search_by_market_name
        True,        # spread_product_type
        True,        # cfd_product_type
        False,       # binary_product_type
        True,        # ascending_order
        False,       # include_options
        123456,      # client_account_id
        page=0,
        page_size=10,
        order_by="Name",
    )
    print("total matches:", results.total_number_of_results)
```

The keyword-only options and their defaults are `page=0`, `page_size=10`,
`order_by="Name"`, `use_mobile_short_name=False`, and `trading_account_id=None`.

## Fetch open positions

`list_open_positions` takes an optional keyword-only `trading_account_id`. It returns a
`ListOpenPositionsResponseDTO` whose `open_positions` field is a list of position DTOs.

```python
from stonepy import StoneXClient, ClientConfig

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    response = client.order.list_open_positions(trading_account_id=123456)
    for position in response.open_positions or []:
        print(position.order_id, position.market_name, position.direction)
```

## Place a trade order and cancel an order

`place_order` accepts a `NewStopLimitOrderRequestDTO` and returns an
`ApiTradeOrderResponseDTO`. `cancel_order` accepts a `CancelOrderRequestDTO`.

!!! warning
    The snippet below places and cancels **live orders** against your account. Run it only
    against a demo/test account, and double-check `market_id`, `trading_account_id`,
    `direction`, `quantity`, and `trigger_price` before executing. Real orders move real
    money.

```python
from decimal import Decimal

from stonepy import StoneXClient, ClientConfig
from stonepy.models import NewStopLimitOrderRequestDTO, CancelOrderRequestDTO

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    placed = client.order.place_order(
        NewStopLimitOrderRequestDTO(
            order_id=0,
            market_id=400481000,
            currency="GBP",
            auto_rollover=False,
            direction="buy",
            position_method_id=1,
            quantity=Decimal("1"),
            bid_price=Decimal("0"),
            offer_price=Decimal("0"),
            audit_id="",
            trading_account_id=123456,
            applicability="GTC",
            expiry_date_time_utc=None,
            guaranteed=False,
            trigger_price=Decimal("1.2500"),
            reference="stonepy",
            allocation_profile_id=0,
            order_reference="",
            source="stonepy",
        )
    )
    print("place status:", placed.status, "order id:", placed.order_id)

    # Cancel the order we just placed.
    cancelled = client.order.cancel_order(
        CancelOrderRequestDTO(
            order_id=placed.order_id or 0,
            trading_account_id=123456,
            market_id=400481000,
            reference="stonepy",
        )
    )
    print("cancel status:", cancelled.status)
```

## List and save a watchlist

`get_watchlists(client_account_id)` returns the client's watchlists. `save_watchlist`
accepts a `SaveWatchlistRequestDTO` containing a single `ApiClientAccountWatchlistDTO`
(with `ApiClientAccountWatchlistItemDTO` items) and returns the saved
`watchlist_id`.

```python
from stonepy import StoneXClient, ClientConfig
from stonepy.models import (
    SaveWatchlistRequestDTO,
    ApiClientAccountWatchlistDTO,
    ApiClientAccountWatchlistItemDTO,
)

config = ClientConfig.from_env()
client_account_id = 123456

with StoneXClient(config) as client:
    # List existing watchlists.
    existing = client.watchlist.get_watchlists(client_account_id)
    for wl in existing.client_account_watchlists or []:
        print(wl.watchlist_id, wl.watchlist_description)

    # Save a new watchlist holding a single market.
    saved = client.watchlist.save_watchlist(
        SaveWatchlistRequestDTO(
            client_account_id=client_account_id,
            watchlist=ApiClientAccountWatchlistDTO(
                watchlist_description="FX Majors",
                display_order=1,
                items=[
                    ApiClientAccountWatchlistItemDTO(
                        market_id=400481000,
                        display_order=1,
                    )
                ],
            ),
        )
    )
    print("saved watchlist id:", saved.watchlist_id)
```

!!! note
    `get_watchlists_list(client_account_id, ids, ...)` is a related method that fetches
    specific watchlists by their `ids` (a `list[int]`), with optional `include_items` and
    `include_market_information` keyword flags.
