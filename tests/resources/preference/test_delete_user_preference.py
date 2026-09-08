from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import UnspecifiedResponse
from stonepy.client import AsyncStoneXClient, StoneXClient


@respx.mock
def test_delete_user_preference_returns_response() -> None:
    route = respx.delete("https://api.example/v2/Preference").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        preferences: list[str] = []
        resp = client.preference.delete_user_preference(preferences=preferences)
        assert isinstance(resp, UnspecifiedResponse)
        assert route.called
        assert route.calls[0].request.method == "DELETE"
        assert route.calls[0].request.url.path == "/v2/Preference"
    finally:
        client.close()


@respx.mock
def test_delete_user_preference_async() -> None:
    async def run() -> None:
        route = respx.delete("https://api.example/v2/Preference").mock(
            return_value=httpx.Response(200, json={})
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            preferences: list[str] = []
            resp = await client.preference.delete_user_preference(preferences=preferences)
            assert isinstance(resp, UnspecifiedResponse)
            assert route.called
            assert route.calls[0].request.method == "DELETE"
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("body", [b"", b"null"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_delete_user_preference_returns_unspecified_response_for_empty_body(
    body: bytes, asynchronous: bool
) -> None:
    response = _call_delete_user_preference(body, asynchronous)
    assert isinstance(response, UnspecifiedResponse)
    assert response.model_extra == {}


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_delete_user_preference_retains_unexpected_object_fields(asynchronous: bool) -> None:
    response = _call_delete_user_preference(b'{"a":1}', asynchronous)
    assert response.model_extra == {"a": 1}


def _call_delete_user_preference(body: bytes, asynchronous: bool) -> UnspecifiedResponse:
    respx.request("DELETE", "https://api.example/v2/Preference").respond(200, content=body)

    async def run() -> UnspecifiedResponse:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "user")
            return await client.preference.delete_user_preference(preferences=[])

    if asynchronous:
        return asyncio.run(run())
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        client._ctx.session.set_token("TOKEN", "user")
        return client.preference.delete_user_preference(preferences=[])
