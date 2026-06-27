from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import (
    ApiClientPreferencesOverridenSettingsSaveRequestDTO,
    ApiClientPreferencesOverridenSettingsSaveResponseDTO,
)

_RESPONSE_BODY = '{"Successful":false,"Settings":{"Price Tolerance":{"IsDirty":false,"Value":"1.23"},"MarginFactorPercentage":{"IsDirty":false,"Value":"1.23"}}}'  # noqa: E501


@respx.mock
def test_save_overridden_settings_returns_response() -> None:
    route = respx.post("https://api.example/clientpreference/overriddensettings/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiClientPreferencesOverridenSettingsSaveRequestDTO.model_construct()
        resp = client.clientpreference.save_overridden_settings(request)
        assert isinstance(resp, ApiClientPreferencesOverridenSettingsSaveResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/clientpreference/overriddensettings/save"
    finally:
        client.close()


@respx.mock
def test_save_overridden_settings_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/clientpreference/overriddensettings/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiClientPreferencesOverridenSettingsSaveRequestDTO.model_construct()
            resp = await client.clientpreference.save_overridden_settings(request)
            assert isinstance(resp, ApiClientPreferencesOverridenSettingsSaveResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
