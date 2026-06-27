from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import DeleteWatchlistResponseDTO

_RESPONSE_BODY = '{"Deleted":false}'


@respx.mock
def test_delete_watchlist_returns_response() -> None:
    route = respx.delete("https://api.example/watchlist/v2/watchlists").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        watchlist_id = 1
        resp = client.watchlist.delete_watchlist(client_account_id, watchlist_id)
        assert isinstance(resp, DeleteWatchlistResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "DELETE"
        assert route.calls[0].request.url.path == "/watchlist/v2/watchlists"
    finally:
        client.close()


@respx.mock
def test_delete_watchlist_async() -> None:
    async def run() -> None:
        route = respx.delete("https://api.example/watchlist/v2/watchlists").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            watchlist_id = 1
            resp = await client.watchlist.delete_watchlist(client_account_id, watchlist_id)
            assert isinstance(resp, DeleteWatchlistResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "DELETE"
        finally:
            await client.aclose()

    asyncio.run(run())
