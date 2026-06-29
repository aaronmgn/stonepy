from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListWatchlistResponseDTO

_RESPONSE_BODY = '{"ClientAccountId":1,"ClientAccountWatchlists":[]}'


@respx.mock
def test_get_watchlists_returns_response() -> None:
    route = respx.get("https://api.example/v2/watchlists").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        resp = client.watchlist.get_watchlists(client_account_id)
        assert isinstance(resp, ListWatchlistResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/watchlists"
    finally:
        client.close()


@respx.mock
def test_get_watchlists_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/watchlists").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            resp = await client.watchlist.get_watchlists(client_account_id)
            assert isinstance(resp, ListWatchlistResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
