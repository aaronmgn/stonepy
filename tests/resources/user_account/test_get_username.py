from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiUsernameResponseDTO

_RESPONSE_BODY = '{"TradingAccountCode":"x","Username":"x"}'


@respx.mock
def test_get_username_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/username").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        session_id = "x"
        client_account_id = 1
        resp = client.user_account.get_username(session_id, client_account_id)
        assert isinstance(resp, ApiUsernameResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/username"
        assert dict(route.calls[0].request.url.params) == {
            "sessionId": "x",
            "clientAccountId": "1",
        }
    finally:
        client.close()


@respx.mock
def test_get_username_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/username").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            session_id = "x"
            client_account_id = 1
            resp = await client.user_account.get_username(session_id, client_account_id)
            assert isinstance(resp, ApiUsernameResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {
                "sessionId": "x",
                "clientAccountId": "1",
            }
        finally:
            await client.aclose()

    asyncio.run(run())
