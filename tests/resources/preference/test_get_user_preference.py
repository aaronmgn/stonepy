from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetPreferencesResponseDTO

_RESPONSE_BODY = '{"Preferences":[{"Key":"x","Value":"x"}]}'


@respx.mock
def test_get_user_preference_returns_response() -> None:
    route = respx.get("https://api.example/preference/v2/Preferences").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        preferences: list[str] | None = []
        resp = client.preference.get_user_preference(preferences=preferences)
        assert isinstance(resp, ApiGetPreferencesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/preference/v2/Preferences"
    finally:
        client.close()


@respx.mock
def test_get_user_preference_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/preference/v2/Preferences").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            preferences: list[str] | None = []
            resp = await client.preference.get_user_preference(preferences=preferences)
            assert isinstance(resp, ApiGetPreferencesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
