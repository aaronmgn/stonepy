from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetWallSubItemsResponseDTO

_RESPONSE_BODY = '{"WallItems":{"WallItemId":1,"ParentWallItemId":1,"ScreenName":"x","CommentText":"x","FlaggedAsInappropriate":false,"CreateDate":"/Date(1577836800000)/","NoOfSubComments":1}}'  # noqa: E501


@respx.mock
def test_get_wall_sub_items_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/getwallsubitems").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.user_account.get_wall_sub_items()
        assert isinstance(resp, ApiGetWallSubItemsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/getwallsubitems"
    finally:
        client.close()


@respx.mock
def test_get_wall_sub_items_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/getwallsubitems").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.user_account.get_wall_sub_items()
            assert isinstance(resp, ApiGetWallSubItemsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
