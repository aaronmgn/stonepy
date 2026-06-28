from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import HistoricalOrdersResponseDTO

_RESPONSE_BODY = '{"HistoricalOrders":[{"MarketName":"x","Rank":1,"EntryPrice":"1.23","ExitPrice":"1.23","RealisedPnL":"1.23","SignalStatus":1,"Duration":1,"OrderStatus":1,"Reason":"x"}]}'  # noqa: E501


@respx.mock
def test_get_historical_orders_returns_response() -> None:
    route = respx.get("https://api.example/pm/orders/historical").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.get_historical_orders()
        assert isinstance(resp, HistoricalOrdersResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pm/orders/historical"
    finally:
        client.close()


@respx.mock
def test_get_historical_orders_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pm/orders/historical").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.get_historical_orders()
            assert isinstance(resp, HistoricalOrdersResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
