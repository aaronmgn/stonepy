from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListNewsHeadlinesRequestDTO, ListNewsHeadlinesResponseDTO

_RESPONSE_BODY = '{"Headlines":[{"Story":"x","StoryInHtml":"x"}]}'


@respx.mock
def test_list_news_headlines_returns_response() -> None:
    route = respx.post("https://api.example/news/headlines").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ListNewsHeadlinesRequestDTO.model_construct()
        resp = client.news.list_news_headlines(request)
        assert isinstance(resp, ListNewsHeadlinesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/news/headlines"
    finally:
        client.close()


@respx.mock
def test_list_news_headlines_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/news/headlines").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ListNewsHeadlinesRequestDTO.model_construct()
            resp = await client.news.list_news_headlines(request)
            assert isinstance(resp, ListNewsHeadlinesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
