from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiClientPreferencesOverridenSettingsGetResponseDTO

_RESPONSE_BODY = '{"Successful":false,"Settings":{"Price Tolerance":{"Value":"1.23"},"MarginFactorPercentage":{"CanModify":false,"Value":"1.23","MinValue":"1.23","MaxValue":"1.23"}}}'  # noqa: E501


@respx.mock
def test_get_overridden_settings_returns_response() -> None:
    route = respx.post("https://api.example/clientpreference/overriddensettings/get").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.clientpreference.get_overridden_settings()
        assert isinstance(resp, ApiClientPreferencesOverridenSettingsGetResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/clientpreference/overriddensettings/get"
    finally:
        client.close()


@respx.mock
def test_get_overridden_settings_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/clientpreference/overriddensettings/get").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.clientpreference.get_overridden_settings()
            assert isinstance(resp, ApiClientPreferencesOverridenSettingsGetResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
