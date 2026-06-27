from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListMarketSearchPaginatedResponseDTO

_RESPONSE_BODY = '{"TotalNumberOfResults":1}'


@respx.mock
def test_list_market_search_paginated_returns_response() -> None:
    route = respx.get("https://api.example/market/searchpages").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        query = "x"
        search_by_market_code = False
        search_by_market_name = False
        spread_product_type = False
        cfd_product_type = False
        binary_product_type = False
        ascending_order = False
        include_options = False
        trading_account_id = 1
        client_account_id = 1
        page = 1
        page_size = 1
        order_by = "x"
        use_mobile_short_name = False
        resp = client.market.list_market_search_paginated(
            query,
            search_by_market_code,
            search_by_market_name,
            spread_product_type,
            cfd_product_type,
            binary_product_type,
            ascending_order,
            include_options,
            client_account_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            use_mobile_short_name=use_mobile_short_name,
            trading_account_id=trading_account_id,
        )
        assert isinstance(resp, ListMarketSearchPaginatedResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/searchpages"
    finally:
        client.close()


@respx.mock
def test_list_market_search_paginated_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/searchpages").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            query = "x"
            search_by_market_code = False
            search_by_market_name = False
            spread_product_type = False
            cfd_product_type = False
            binary_product_type = False
            ascending_order = False
            include_options = False
            trading_account_id = 1
            client_account_id = 1
            page = 1
            page_size = 1
            order_by = "x"
            use_mobile_short_name = False
            resp = await client.market.list_market_search_paginated(
                query,
                search_by_market_code,
                search_by_market_name,
                spread_product_type,
                cfd_product_type,
                binary_product_type,
                ascending_order,
                include_options,
                client_account_id,
                page=page,
                page_size=page_size,
                order_by=order_by,
                use_mobile_short_name=use_mobile_short_name,
                trading_account_id=trading_account_id,
            )
            assert isinstance(resp, ListMarketSearchPaginatedResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
