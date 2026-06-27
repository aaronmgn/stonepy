# Quickstart

## Install

```bash
pip install stonepy
```

## Create a client and log on

The client is a context manager. Log on once, then call any resource group; the session token is
attached to every subsequent request automatically.

=== "Sync"

    ```python
    from stonepy import ClientConfig, StoneXClient
    from stonepy.models import ApiLogOnRequestDTO

    config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

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
        markets = client.market.list_market_search_paginated(
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
            page_size=20,
        )
        print(markets.total_number_of_results)
    ```

=== "Async"

    ```python
    from stonepy import AsyncStoneXClient, ClientConfig
    from stonepy.models import ApiLogOnRequestDTO

    config = ClientConfig(base_url="https://ciapi.cityindex.com/TradingAPI")

    async with AsyncStoneXClient(config) as client:
        await client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="username",
                Password="password",
                AppKey="app-key",
                AppVersion="stonepy",
                AppComments="",
            )
        )
        markets = await client.market.list_market_search_paginated(
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
            page_size=20,
        )
        print(markets.total_number_of_results)
    ```

Use `close()` for sync clients (or `aclose()` for async) when you are not using a `with` block.

## Configure from the environment

```python
from stonepy import ClientConfig, StoneXClient

config = ClientConfig.from_env()

with StoneXClient(config) as client:
    ...
```

`ClientConfig.from_env()` reads `STONEX_BASE_URL`, `STONEX_APP_KEY`, `STONEX_USERNAME`, and
`STONEX_PASSWORD`. `STONEX_BASE_URL` is required unless you pass `base_url=`.

If you supply credentials (directly or via `from_env()`), the client also refreshes the session
automatically before the token expires - see [Authentication & sessions](guide/authentication.md).

## Next steps

- [Authentication & sessions](guide/authentication.md)
- [Error handling](guide/error-handling.md)
- [Pagination](guide/pagination.md)
- [API reference](api/client.md)
