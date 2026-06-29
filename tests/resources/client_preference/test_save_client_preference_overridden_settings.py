from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import (
    ApiClientPreferencesOverriddenSettingsSaveRequestDTO,
    ApiClientPreferencesOverriddenSettingsSaveResponseDTO,
)

_RESPONSE_BODY = '{"Successful":false}'


@respx.mock
def test_save_client_preference_overridden_settings_returns_response() -> None:
    route = respx.post("https://api.example/v2/clientPreference/overriddenSettings/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiClientPreferencesOverriddenSettingsSaveRequestDTO.model_construct()
        resp = client.client_preference.save_client_preference_overridden_settings(request)
        assert isinstance(resp, ApiClientPreferencesOverriddenSettingsSaveResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/clientPreference/overriddenSettings/save"
    finally:
        client.close()


@respx.mock
def test_save_client_preference_overridden_settings_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/clientPreference/overriddenSettings/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiClientPreferencesOverriddenSettingsSaveRequestDTO.model_construct()
            resp = await client.client_preference.save_client_preference_overridden_settings(
                request
            )
            assert isinstance(resp, ApiClientPreferencesOverriddenSettingsSaveResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
