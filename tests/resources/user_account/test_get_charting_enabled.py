from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import ResponseModel
from stonepy.client import AsyncStoneXClient, StoneXClient

_RESPONSE_BODY = "{}"


@respx.mock
def test_get_charting_enabled_returns_response() -> None:
    route = respx.get("https://api.example/useraccount/1/ChartingEnabled").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        id = "1"
        resp = client.user_account.get_charting_enabled(id)
        assert isinstance(resp, ResponseModel)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/useraccount/1/ChartingEnabled"
    finally:
        client.close()


@respx.mock
def test_get_charting_enabled_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/useraccount/1/ChartingEnabled").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            id = "1"
            resp = await client.user_account.get_charting_enabled(id)
            assert isinstance(resp, ResponseModel)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
