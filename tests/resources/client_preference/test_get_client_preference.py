from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetClientPreferenceResponseDTO

_RESPONSE_BODY = '{"ClientPreference":{"Key":"x","Value":"x"}}'


@respx.mock
def test_get_client_preference_returns_response() -> None:
    route = respx.get("https://api.example/clientPreference/v2/clientPreference").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        key = "x"
        resp = client.client_preference.get_client_preference(client_account_id, key)
        assert isinstance(resp, ApiGetClientPreferenceResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/clientPreference/v2/clientPreference"
    finally:
        client.close()


@respx.mock
def test_get_client_preference_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/clientPreference/v2/clientPreference").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            key = "x"
            resp = await client.client_preference.get_client_preference(client_account_id, key)
            assert isinstance(resp, ApiGetClientPreferenceResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
