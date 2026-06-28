from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListNewsHeadlinesResponseDTO

_RESPONSE_BODY = '{"Headlines":[{"Story":"x","StoryInHtml":"x"}]}'


@respx.mock
def test_list_news_headlines_with_source_returns_response() -> None:
    route = respx.get("https://api.example/news/x/x").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        source = "x"
        category = "x"
        resp = client.news.list_news_headlines_with_source(source, category)
        assert isinstance(resp, ListNewsHeadlinesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/news/x/x"
    finally:
        client.close()


@respx.mock
def test_list_news_headlines_with_source_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/news/x/x").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            source = "x"
            category = "x"
            resp = await client.news.list_news_headlines_with_source(source, category)
            assert isinstance(resp, ListNewsHeadlinesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
