from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient


@respx.mock
def test_get_market_report_headlines_returns_response() -> None:
    route = respx.get("https://api.example/news/marketreportheadlines").mock(
        return_value=httpx.Response(200, json={"Headlines": []})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = 1
        culture_id = 1
        max_results = 1
        resp = client.news.get_market_report_headlines(
            market_id, culture_id, max_results=max_results
        )
        assert resp.model_dump(by_alias=True) == {"Headlines": []}
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/news/marketreportheadlines"
    finally:
        client.close()


@respx.mock
def test_get_market_report_headlines_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/news/marketreportheadlines").mock(
            return_value=httpx.Response(200, json={"Headlines": []})
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = 1
            culture_id = 1
            max_results = 1
            resp = await client.news.get_market_report_headlines(
                market_id, culture_id, max_results=max_results
            )
            assert resp.model_dump(by_alias=True) == {"Headlines": []}
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
