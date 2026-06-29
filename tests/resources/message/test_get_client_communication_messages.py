from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiClientCommunicationResponseDTO

_RESPONSE_BODY = '{"ClientCommunicationMessages":[]}'


@respx.mock
def test_get_client_communication_messages_returns_response() -> None:
    route = respx.get("https://api.example/v2/message/clientCommunicationMessages").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        culture_id = 1
        resp = client.message.get_client_communication_messages(
            client_account_id, culture_id=culture_id
        )
        assert isinstance(resp, ApiClientCommunicationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/message/clientCommunicationMessages"
    finally:
        client.close()


@respx.mock
def test_get_client_communication_messages_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/message/clientCommunicationMessages").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            culture_id = 1
            resp = await client.message.get_client_communication_messages(
                client_account_id, culture_id=culture_id
            )
            assert isinstance(resp, ApiClientCommunicationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
