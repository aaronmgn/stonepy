from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetAllTradesWallResponseDTO

_RESPONSE_BODY = '{"TradeActions":[{"TradeActionId":1,"OrderId":1,"Direction":"x","Quantity":"1.23","Price":"1.23","TradeType":"x","MarketID":1,"MarketName":"x","MarketType":"x","LastChangedDateTimeUTC":"/Date(1577836800000)/","ClientID":1,"Avatar":"x","FacebookID":"x","ScreenName":"x","FirstName":"x","LastName":"x","ROI":"1.23"}]}'  # noqa: E501


@respx.mock
def test_get_all_trades_wall_returns_response() -> None:
    route = respx.get("https://api.example/order/getalltradeswallinfo").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        direction = "x"
        number_of_results = 1
        resp = client.order.get_all_trades_wall(direction, number_of_results)
        assert isinstance(resp, GetAllTradesWallResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/getalltradeswallinfo"
    finally:
        client.close()


@respx.mock
def test_get_all_trades_wall_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/getalltradeswallinfo").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            direction = "x"
            number_of_results = 1
            resp = await client.order.get_all_trades_wall(direction, number_of_results)
            assert isinstance(resp, GetAllTradesWallResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
