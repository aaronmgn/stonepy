from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListMarketInformationResponseDTO, MultipleMarketInformationRequestDTO

_RESPONSE_BODY = '{"MarketInformations":[]}'


@respx.mock
def test_list_market_information_returns_response() -> None:
    route = respx.post("https://api.example/v2/market/information").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = MultipleMarketInformationRequestDTO.model_construct()
        resp = client.market.list_market_information(request)
        assert isinstance(resp, ListMarketInformationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/market/information"
    finally:
        client.close()


@respx.mock
def test_list_market_information_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/market/information").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = MultipleMarketInformationRequestDTO.model_construct()
            resp = await client.market.list_market_information(request)
            assert isinstance(resp, ListMarketInformationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
