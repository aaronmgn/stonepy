from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import UnspecifiedResponse
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiSavePreferencesRequestDTO


@respx.mock
def test_save_user_preference_returns_response() -> None:
    route = respx.post("https://api.example/v2/Preference/save").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiSavePreferencesRequestDTO.model_construct()
        resp = client.preference.save_user_preference(request)
        assert isinstance(resp, UnspecifiedResponse)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/Preference/save"
    finally:
        client.close()


@respx.mock
def test_save_user_preference_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/Preference/save").mock(
            return_value=httpx.Response(200, json={})
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiSavePreferencesRequestDTO.model_construct()
            resp = await client.preference.save_user_preference(request)
            assert isinstance(resp, UnspecifiedResponse)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("body", [b"", b"null"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_save_user_preference_returns_unspecified_response_for_empty_body(
    body: bytes, asynchronous: bool
) -> None:
    response = _call_save_user_preference(body, asynchronous)
    assert isinstance(response, UnspecifiedResponse)
    assert response.model_extra == {}


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_save_user_preference_retains_unexpected_object_fields(asynchronous: bool) -> None:
    response = _call_save_user_preference(b'{"a":1}', asynchronous)
    assert response.model_extra == {"a": 1}


def _call_save_user_preference(body: bytes, asynchronous: bool) -> UnspecifiedResponse:
    respx.request("POST", "https://api.example/v2/Preference/save").respond(200, content=body)

    async def run() -> UnspecifiedResponse:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "user")
            return await client.preference.save_user_preference(
                ApiSavePreferencesRequestDTO.model_validate({"Preferences": []})
            )

    if asynchronous:
        return asyncio.run(run())
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        client._ctx.session.set_token("TOKEN", "user")
        return client.preference.save_user_preference(
            ApiSavePreferencesRequestDTO.model_validate({"Preferences": []})
        )
