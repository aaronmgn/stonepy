from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiClientApplicationMessageTranslationResponseDTO

_RESPONSE_BODY = '{"TranslationKeyValuePairs":[{"Key":"x","Value":"x"}]}'


@respx.mock
def test_get_client_application_message_translation_returns_response() -> None:
    route = respx.get("https://api.example/message/translation").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_application_id = 1
        culture_id = 1
        account_operator_id = 1
        resp = client.message.get_client_application_message_translation(
            client_application_id, culture_id, account_operator_id
        )
        assert isinstance(resp, ApiClientApplicationMessageTranslationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/message/translation"
    finally:
        client.close()


@respx.mock
def test_get_client_application_message_translation_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/message/translation").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_application_id = 1
            culture_id = 1
            account_operator_id = 1
            resp = await client.message.get_client_application_message_translation(
                client_application_id, culture_id, account_operator_id
            )
            assert isinstance(resp, ApiClientApplicationMessageTranslationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
