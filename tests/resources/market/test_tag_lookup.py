from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import MarketInformationTagLookupResponseDTO

_RESPONSE_BODY = '{"Tags":[{"Children":[]}]}'


@respx.mock
def test_tag_lookup_returns_response() -> None:
    route = respx.get("https://api.example/market/v2/market/tagLookup").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = "x"
        resp = client.market.tag_lookup(client_account_id)
        assert isinstance(resp, MarketInformationTagLookupResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/v2/market/tagLookup"
        assert dict(route.calls[0].request.url.params) == {"clientAccountId": "x"}
    finally:
        client.close()


@respx.mock
def test_tag_lookup_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/v2/market/tagLookup").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = "x"
            resp = await client.market.tag_lookup(client_account_id)
            assert isinstance(resp, MarketInformationTagLookupResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
