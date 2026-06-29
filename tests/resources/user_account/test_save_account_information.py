from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiAccountInformationSaveRequestDTO, ApiAccountInformationSaveResponseDTO

_RESPONSE_BODY = "{}"


@respx.mock
def test_save_account_information_returns_response() -> None:
    route = respx.post("https://api.example/v2/userAccount/Save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiAccountInformationSaveRequestDTO.model_construct()
        resp = client.user_account.save_account_information(request)
        assert isinstance(resp, ApiAccountInformationSaveResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/userAccount/Save"
    finally:
        client.close()


@respx.mock
def test_save_account_information_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/userAccount/Save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiAccountInformationSaveRequestDTO.model_construct()
            resp = await client.user_account.save_account_information(request)
            assert isinstance(resp, ApiAccountInformationSaveResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
