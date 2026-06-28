from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiSaveSignalPreferencesResponseDTO

_RESPONSE_BODY = "{}"


@respx.mock
def test_save_signal_preferences_returns_response() -> None:
    route = respx.post("https://api.example/pm/preferences").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.save_signal_preferences()
        assert isinstance(resp, ApiSaveSignalPreferencesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/pm/preferences"
    finally:
        client.close()


@respx.mock
def test_save_signal_preferences_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/pm/preferences").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.save_signal_preferences()
            assert isinstance(resp, ApiSaveSignalPreferencesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
