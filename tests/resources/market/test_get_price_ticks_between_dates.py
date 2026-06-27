from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetPriceTickResponseDTO

_RESPONSE_BODY = '{"PriceTicks":[{"TickDate":"/Date(1577836800000)/","Price":"1.23"}]}'


@respx.mock
def test_get_price_ticks_between_dates_returns_response() -> None:
    route = respx.get("https://api.example/market/x/tickhistorybetween").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = "x"
        max_results = 1
        from_time_stamp_utc = 1
        to_timestamp_utc = 1
        price_type = "x"
        resp = client.market.get_price_ticks_between_dates(
            market_id, from_time_stamp_utc, to_timestamp_utc, price_type, max_results=max_results
        )
        assert isinstance(resp, GetPriceTickResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/x/tickhistorybetween"
    finally:
        client.close()


@respx.mock
def test_get_price_ticks_between_dates_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/x/tickhistorybetween").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = "x"
            max_results = 1
            from_time_stamp_utc = 1
            to_timestamp_utc = 1
            price_type = "x"
            resp = await client.market.get_price_ticks_between_dates(
                market_id,
                from_time_stamp_utc,
                to_timestamp_utc,
                price_type,
                max_results=max_results,
            )
            assert isinstance(resp, GetPriceTickResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
