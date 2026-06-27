from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListMarketSearchResponseDTO

_RESPONSE_BODY = '{"Markets":[{"MarketId":1,"Name":"x","Weighting":1}]}'


@respx.mock
def test_list_market_search_returns_response() -> None:
    route = respx.get("https://api.example/market/search").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        search_by_market_code = False
        search_by_market_name = False
        spread_product_type = False
        cfd_product_type = False
        binary_product_type = False
        include_options = False
        query = "x"
        trading_account_id = 1
        max_results = 1
        client_account_id = 1
        use_mobile_short_name = False
        resp = client.market.list_market_search(
            search_by_market_code,
            search_by_market_name,
            spread_product_type,
            cfd_product_type,
            binary_product_type,
            include_options,
            query,
            max_results,
            client_account_id,
            trading_account_id=trading_account_id,
            use_mobile_short_name=use_mobile_short_name,
        )
        assert isinstance(resp, ListMarketSearchResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/search"
    finally:
        client.close()


@respx.mock
def test_list_market_search_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/search").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            search_by_market_code = False
            search_by_market_name = False
            spread_product_type = False
            cfd_product_type = False
            binary_product_type = False
            include_options = False
            query = "x"
            trading_account_id = 1
            max_results = 1
            client_account_id = 1
            use_mobile_short_name = False
            resp = await client.market.list_market_search(
                search_by_market_code,
                search_by_market_name,
                spread_product_type,
                cfd_product_type,
                binary_product_type,
                include_options,
                query,
                max_results,
                client_account_id,
                trading_account_id=trading_account_id,
                use_mobile_short_name=use_mobile_short_name,
            )
            assert isinstance(resp, ListMarketSearchResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
