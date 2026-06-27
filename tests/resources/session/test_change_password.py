from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiChangePasswordRequestDTO, ApiChangePasswordResponseDTO

_RESPONSE_BODY = '{"IsPasswordChanged":false}'


@respx.mock
def test_change_password_returns_response() -> None:
    route = respx.post("https://api.example/session/changePassword").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiChangePasswordRequestDTO.model_construct()
        resp = client.session.change_password(request)
        assert isinstance(resp, ApiChangePasswordResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/session/changePassword"
    finally:
        client.close()


@respx.mock
def test_change_password_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/session/changePassword").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiChangePasswordRequestDTO.model_construct()
            resp = await client.session.change_password(request)
            assert isinstance(resp, ApiChangePasswordResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
