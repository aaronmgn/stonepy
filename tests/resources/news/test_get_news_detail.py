from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetNewsDetailResponseDTO

_RESPONSE_BODY = '{"NewsDetail":{"Story":"x"}}'


@respx.mock
def test_get_news_detail_returns_response() -> None:
    route = respx.get("https://api.example/news/x/1").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        source = "x"
        story_id = 1
        resp = client.news.get_news_detail(source, story_id)
        assert isinstance(resp, GetNewsDetailResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/news/x/1"
    finally:
        client.close()


@respx.mock
def test_get_news_detail_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/news/x/1").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            source = "x"
            story_id = 1
            resp = await client.news.get_news_detail(source, story_id)
            assert isinstance(resp, GetNewsDetailResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
