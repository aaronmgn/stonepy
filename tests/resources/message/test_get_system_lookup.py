from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiLookupResponseDTO

_RESPONSE_BODY = '{"CultureId":1,"LookupEntityName":"x","ApiLookupDTOList":[{"Id":1,"Description":"x","DisplayOrder":1,"TranslationTextId":1,"TranslationText":"x","IsActive":false,"IsAllowed":false}],"ApiCultureLookupDTOList":[{"Code":"x"}]}'  # noqa: E501


@respx.mock
def test_get_system_lookup_returns_response() -> None:
    route = respx.get("https://api.example/message/lookup").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        lookup_entity_name = "x"
        culture_id = 1
        resp = client.message.get_system_lookup(lookup_entity_name, culture_id)
        assert isinstance(resp, ApiLookupResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/message/lookup"
    finally:
        client.close()


@respx.mock
def test_get_system_lookup_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/message/lookup").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            lookup_entity_name = "x"
            culture_id = 1
            resp = await client.message.get_system_lookup(lookup_entity_name, culture_id)
            assert isinstance(resp, ApiLookupResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
