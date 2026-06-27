from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import ResponseModel
from stonepy.client import AsyncStoneXClient, StoneXClient


@respx.mock
def test_delete_user_preference_returns_response() -> None:
    route = respx.delete("https://api.example/preference/v2/Preference").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        preferences: list[str] = []
        resp = client.preference.delete_user_preference(preferences=preferences)
        assert isinstance(resp, ResponseModel)
        assert route.called
        assert route.calls[0].request.method == "DELETE"
        assert route.calls[0].request.url.path == "/preference/v2/Preference"
    finally:
        client.close()


@respx.mock
def test_delete_user_preference_async() -> None:
    async def run() -> None:
        route = respx.delete("https://api.example/preference/v2/Preference").mock(
            return_value=httpx.Response(200, json={})
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            preferences: list[str] = []
            resp = await client.preference.delete_user_preference(preferences=preferences)
            assert isinstance(resp, ResponseModel)
            assert route.called
            assert route.calls[0].request.method == "DELETE"
        finally:
            await client.aclose()

    asyncio.run(run())
