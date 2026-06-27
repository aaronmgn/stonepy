from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import MarketSpreadData

_RESPONSE_BODY = '{"MarketId":1,"OutOfHours":"1.23","InHours":"1.23","MarkUp":"1.23","MarkUpUnits":"1.23","TypicalSpread":"1.23","MinSpread":"1.23"}'  # noqa: E501


@respx.mock
def test_get_market_spread_returns_response() -> None:
    route = respx.get("https://api.example/market/v2/market/spread").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = "x"
        market_id = "x"
        resp = client.market.get_market_spread(client_account_id, market_id)
        assert isinstance(resp, MarketSpreadData)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/v2/market/spread"
        assert dict(route.calls[0].request.url.params) == {
            "clientAccountId": "x",
            "marketId": "x",
        }
    finally:
        client.close()


@respx.mock
def test_get_market_spread_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/v2/market/spread").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = "x"
            market_id = "x"
            resp = await client.market.get_market_spread(client_account_id, market_id)
            assert isinstance(resp, MarketSpreadData)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {
                "clientAccountId": "x",
                "marketId": "x",
            }
        finally:
            await client.aclose()

    asyncio.run(run())
