from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetPriceBarResponseDTO

_RESPONSE_BODY = '{"PriceBars":[{"BarDate":"/Date(1577836800000)/","Open":"1.23","High":"1.23","Low":"1.23","Close":"1.23"}],"PartialPriceBar":{"BarDate":"/Date(1577836800000)/","Open":"1.23","High":"1.23","Low":"1.23","Close":"1.23"}}'  # noqa: E501


@respx.mock
def test_get_latest_price_bars_returns_response() -> None:
    route = respx.get("https://api.example/market/x/barhistory").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = "x"
        interval = "x"
        span = 1
        price_bars = 1
        price_type = "x"
        resp = client.market.get_latest_price_bars(
            market_id, interval, span, price_bars, price_type
        )
        assert isinstance(resp, GetPriceBarResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/x/barhistory"
    finally:
        client.close()


@respx.mock
def test_get_latest_price_bars_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/x/barhistory").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = "x"
            interval = "x"
            span = 1
            price_bars = 1
            price_type = "x"
            resp = await client.market.get_latest_price_bars(
                market_id, interval, span, price_bars, price_type
            )
            assert isinstance(resp, GetPriceBarResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
