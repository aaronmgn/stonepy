from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiLogOffResponseDTO

_RESPONSE_BODY = '{"LoggedOut":false}'


@respx.mock
def test_delete_session_returns_response() -> None:
    route = respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        user_name = "x"
        session = "x"
        resp = client.session.delete_session(user_name, session)
        assert isinstance(resp, ApiLogOffResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/session/deleteSession"
    finally:
        client.close()


@respx.mock
def test_delete_session_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/session/deleteSession").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            user_name = "x"
            session = "x"
            resp = await client.session.delete_session(user_name, session)
            assert isinstance(resp, ApiLogOffResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
