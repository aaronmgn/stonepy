from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetVersionInformationResponseDTO

_RESPONSE_BODY = '{"MinimumRequiredVersion":"x","LatestVersion":"x","UpgradeUrl":"x"}'


@respx.mock
def test_get_version_information_returns_response() -> None:
    route = respx.get("https://api.example/clientapplication/versioninformation").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        app_key = "x"
        account_operator_id = 1
        resp = client.clientapplication.get_version_information(app_key, account_operator_id)
        assert isinstance(resp, GetVersionInformationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/clientapplication/versioninformation"
    finally:
        client.close()


@respx.mock
def test_get_version_information_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/clientapplication/versioninformation").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            app_key = "x"
            account_operator_id = 1
            resp = await client.clientapplication.get_version_information(
                app_key, account_operator_id
            )
            assert isinstance(resp, GetVersionInformationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
