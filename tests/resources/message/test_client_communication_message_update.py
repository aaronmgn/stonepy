from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import (
    ApiClientCommunicationUpdateRequestDTO,
    ApiClientCommunicationUpdateResponseDTO,
)

_RESPONSE_BODY = '{"Success":false}'


@respx.mock
def test_client_communication_message_update_returns_response() -> None:
    route = respx.get("https://api.example/message/ClientCommunicationMessageResponse").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ApiClientCommunicationUpdateRequestDTO.model_construct()
        resp = client.message.client_communication_message_update(request)
        assert isinstance(resp, ApiClientCommunicationUpdateResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/message/ClientCommunicationMessageResponse"
    finally:
        client.close()


@respx.mock
def test_client_communication_message_update_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/message/ClientCommunicationMessageResponse").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ApiClientCommunicationUpdateRequestDTO.model_construct()
            resp = await client.message.client_communication_message_update(request)
            assert isinstance(resp, ApiClientCommunicationUpdateResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
