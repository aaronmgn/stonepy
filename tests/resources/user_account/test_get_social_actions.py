from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetCommunityActionsResponseDTO

_RESPONSE_BODY = '{"CommunityActions":{"CommunityActionId":1,"CommunityActionTypeId":1,"CommunityActionTypeDescription":"x","CreateDate":"/Date(1577836800000)/"}}'  # noqa: E501


@respx.mock
def test_get_social_actions_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/getsocialactions").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.user_account.get_social_actions()
        assert isinstance(resp, ApiGetCommunityActionsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/getsocialactions"
    finally:
        client.close()


@respx.mock
def test_get_social_actions_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/getsocialactions").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.user_account.get_social_actions()
            assert isinstance(resp, ApiGetCommunityActionsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
