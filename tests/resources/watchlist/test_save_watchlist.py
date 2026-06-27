from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SaveWatchlistRequestDTO, SaveWatchlistResponseDTO

_RESPONSE_BODY = '{"WatchlistId":1}'


@respx.mock
def test_save_watchlist_returns_response() -> None:
    route = respx.post("https://api.example/watchlist/v2/watchlists/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = SaveWatchlistRequestDTO.model_construct()
        resp = client.watchlist.save_watchlist(request)
        assert isinstance(resp, SaveWatchlistResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/watchlist/v2/watchlists/save"
    finally:
        client.close()


@respx.mock
def test_save_watchlist_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/watchlist/v2/watchlists/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = SaveWatchlistRequestDTO.model_construct()
            resp = await client.watchlist.save_watchlist(request)
            assert isinstance(resp, SaveWatchlistResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
