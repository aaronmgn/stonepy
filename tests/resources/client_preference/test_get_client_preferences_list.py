from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetClientPreferencesResponseDTO

_RESPONSE_BODY = '{"ClientPreferences":[{"Key":"x","Value":"x"}]}'


@respx.mock
def test_get_client_preferences_list_returns_response() -> None:
    route = respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        keys = ["x"]
        client_account_id = 1
        string = "x"
        resp = client.client_preference.get_client_preferences_list(keys, client_account_id, string)
        assert isinstance(resp, ApiGetClientPreferencesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/clientPreference/list"
    finally:
        client.close()


@respx.mock
def test_get_client_preferences_list_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/clientPreference/list").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            keys = ["x"]
            client_account_id = 1
            string = "x"
            resp = await client.client_preference.get_client_preferences_list(
                keys, client_account_id, string
            )
            assert isinstance(resp, ApiGetClientPreferencesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
