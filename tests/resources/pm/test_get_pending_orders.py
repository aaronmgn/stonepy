from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import PendingOrdersResponseDTO

_RESPONSE_BODY = '{"PendingOrders":[{"TriggerPrice":"1.23","MarketId":1}]}'


@respx.mock
def test_get_pending_orders_returns_response() -> None:
    route = respx.get("https://api.example/pm/orders/pending").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.get_pending_orders()
        assert isinstance(resp, PendingOrdersResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pm/orders/pending"
    finally:
        client.close()


@respx.mock
def test_get_pending_orders_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pm/orders/pending").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.get_pending_orders()
            assert isinstance(resp, PendingOrdersResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
