from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ActiveSignalsResponseDTO

_RESPONSE_BODY = '{"Signals":[{"SignalId":1,"Percentage":"1.23","MarketId":1,"ExpirationDateTime":"/Date(1577836800000)/","Hot":false}]}'  # noqa: E501


@respx.mock
def test_list_active_signals_returns_response() -> None:
    route = respx.get("https://api.example/pm/signals/active").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.list_active_signals()
        assert isinstance(resp, ActiveSignalsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pm/signals/active"
    finally:
        client.close()


@respx.mock
def test_list_active_signals_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pm/signals/active").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.list_active_signals()
            assert isinstance(resp, ActiveSignalsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
