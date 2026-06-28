from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import PreferenceDTO

_RESPONSE_BODY = '{"Key":"x","Value":"x"}'


@respx.mock
def test_get_signal_preferences_returns_response() -> None:
    route = respx.get("https://api.example/pm/preferences").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.get_signal_preferences()
        assert isinstance(resp, PreferenceDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pm/preferences"
    finally:
        client.close()


@respx.mock
def test_get_signal_preferences_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pm/preferences").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.get_signal_preferences()
            assert isinstance(resp, PreferenceDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
