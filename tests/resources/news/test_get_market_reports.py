from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import NewsResponseDTO

_RESPONSE_BODY = '{"News":null}'


@respx.mock
def test_get_market_reports_returns_response() -> None:
    route = respx.get("https://api.example/news/marketreports").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = 1
        culture_id = 1
        max_results = 1
        resp = client.news.get_market_reports(market_id, culture_id, max_results=max_results)
        assert isinstance(resp, NewsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/news/marketreports"
    finally:
        client.close()


@respx.mock
def test_get_market_reports_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/news/marketreports").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = 1
            culture_id = 1
            max_results = 1
            resp = await client.news.get_market_reports(
                market_id, culture_id, max_results=max_results
            )
            assert isinstance(resp, NewsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
