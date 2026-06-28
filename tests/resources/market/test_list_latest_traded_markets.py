from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiListLatestTradedMarketsResponseDTO

_RESPONSE_BODY = '{"TradedMarkets":[{}]}'


@respx.mock
def test_list_latest_traded_markets_returns_response() -> None:
    route = respx.get("https://api.example/market/latesttraded").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        screen_names = ["x"]
        number_of_results = 1
        resp = client.market.list_latest_traded_markets(screen_names, number_of_results)
        assert isinstance(resp, ApiListLatestTradedMarketsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/latesttraded"
    finally:
        client.close()


@respx.mock
def test_list_latest_traded_markets_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/latesttraded").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            screen_names = ["x"]
            number_of_results = 1
            resp = await client.market.list_latest_traded_markets(screen_names, number_of_results)
            assert isinstance(resp, ApiListLatestTradedMarketsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
