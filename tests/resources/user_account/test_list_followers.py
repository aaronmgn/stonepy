from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiListFollowingUsersResponseDTO

_RESPONSE_BODY = '{"FollowedUsers":{}}'


@respx.mock
def test_list_followers_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/followers").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        screen_names = "x"
        resp = client.user_account.list_followers(screen_names)
        assert isinstance(resp, ApiListFollowingUsersResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/followers"
        assert dict(route.calls[0].request.url.params) == {"screenNames": "x"}
    finally:
        client.close()


@respx.mock
def test_list_followers_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/followers").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            screen_names = "x"
            resp = await client.user_account.list_followers(screen_names)
            assert isinstance(resp, ApiListFollowingUsersResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {"screenNames": "x"}
        finally:
            await client.aclose()

    asyncio.run(run())
