from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiValidateSessionRequestDTOv2, ApiValidateSessionResponseDTO

_RESPONSE_BODY = '{"IsAuthenticated":false}'


@respx.mock
def test_validate_session_returns_response() -> None:
    route = respx.post("https://api.example/session/v2/Session/validate").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiValidateSessionRequestDTOv2.model_construct()
        resp = client.session.validate_session(request)
        assert isinstance(resp, ApiValidateSessionResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/session/v2/Session/validate"
    finally:
        client.close()


@respx.mock
def test_validate_session_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/session/v2/Session/validate").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiValidateSessionRequestDTOv2.model_construct()
            resp = await client.session.validate_session(request)
            assert isinstance(resp, ApiValidateSessionResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
