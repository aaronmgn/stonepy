from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiListFollowedUsersResponseDTO

_RESPONSE_BODY = '{"FollowingUsers":{}}'


@respx.mock
def test_list_followed_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/followed").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        screen_names = "x"
        resp = client.user_account.list_followed(screen_names)
        assert isinstance(resp, ApiListFollowedUsersResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/followed"
        assert dict(route.calls[0].request.url.params) == {"screenNames": "x"}
    finally:
        client.close()


@respx.mock
def test_list_followed_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/followed").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            screen_names = "x"
            resp = await client.user_account.list_followed(screen_names)
            assert isinstance(resp, ApiListFollowedUsersResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {"screenNames": "x"}
        finally:
            await client.aclose()

    asyncio.run(run())
