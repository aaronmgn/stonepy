from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetMessagePopupResponseDTO

_RESPONSE_BODY = '{"AskForClientApproval":false,"Message":"x"}'


@respx.mock
def test_get_message_popup_returns_response() -> None:
    route = respx.get("https://api.example/message/popup").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        language = "x"
        client_account_id = 1
        resp = client.message.get_message_popup(language, client_account_id)
        assert isinstance(resp, GetMessagePopupResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/message/popup"
    finally:
        client.close()


@respx.mock
def test_get_message_popup_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/message/popup").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            language = "x"
            client_account_id = 1
            resp = await client.message.get_message_popup(language, client_account_id)
            assert isinstance(resp, GetMessagePopupResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
