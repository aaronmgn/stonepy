from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SecureMessageCount

_RESPONSE_BODY = (
    '{"LegalPartyId":1,"UnreadMessagesCount":1,"ReadMessagesCount":1,"NewMessage":false}'
)


@respx.mock
def test_get_secure_messages_returns_response() -> None:
    route = respx.get("https://api.example/v2/message/SecureMessages").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        legal_party_id = 1
        client_account_id = "x"
        resp = client.message.get_secure_messages(legal_party_id, client_account_id)
        assert isinstance(resp, SecureMessageCount)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/message/SecureMessages"
        assert dict(route.calls[0].request.url.params) == {
            "LegalPartyId": "1",
            "clientAccountId": "x",
        }
    finally:
        client.close()


@respx.mock
def test_get_secure_messages_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/message/SecureMessages").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            legal_party_id = 1
            client_account_id = "x"
            resp = await client.message.get_secure_messages(legal_party_id, client_account_id)
            assert isinstance(resp, SecureMessageCount)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
