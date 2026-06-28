from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiClientPreferencesOverriddenSettingsGetResponseDTO

_RESPONSE_BODY = '{"Successful":false,"Settings":{}}'


@respx.mock
def test_get_client_preference_overridden_settings_returns_response() -> None:
    route = respx.get(
        "https://api.example/clientPreference/v2/clientPreference/overriddenSettings"
    ).mock(return_value=httpx.Response(200, content=_RESPONSE_BODY))
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        resp = client.client_preference.get_client_preference_overridden_settings(client_account_id)
        assert isinstance(resp, ApiClientPreferencesOverriddenSettingsGetResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert (
            route.calls[0].request.url.path
            == "/clientPreference/v2/clientPreference/overriddenSettings"
        )
    finally:
        client.close()


@respx.mock
def test_get_client_preference_overridden_settings_async() -> None:
    async def run() -> None:
        route = respx.get(
            "https://api.example/clientPreference/v2/clientPreference/overriddenSettings"
        ).mock(return_value=httpx.Response(200, content=_RESPONSE_BODY))
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            resp = await client.client_preference.get_client_preference_overridden_settings(
                client_account_id
            )
            assert isinstance(resp, ApiClientPreferencesOverriddenSettingsGetResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
