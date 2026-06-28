from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiTraderSearchResponseDTO

_RESPONSE_BODY = '{"TotalNumberOfResults":1,"Traders":{}}'


@respx.mock
def test_search_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/search").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        page_number = 1
        resp = client.user_account.search(page_number)
        assert isinstance(resp, ApiTraderSearchResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/search"
        assert dict(route.calls[0].request.url.params) == {"pageNumber": "1"}
    finally:
        client.close()


@respx.mock
def test_search_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/search").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            page_number = 1
            resp = await client.user_account.search(page_number)
            assert isinstance(resp, ApiTraderSearchResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {"pageNumber": "1"}
        finally:
            await client.aclose()

    asyncio.run(run())
