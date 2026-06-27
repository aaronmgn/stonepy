from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiSaveMarketInformationResponseDTO, SaveMarketInformationRequestDTO

_RESPONSE_BODY = "{}"


@respx.mock
def test_save_market_information_returns_response() -> None:
    route = respx.post("https://api.example/market/information/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = SaveMarketInformationRequestDTO.model_construct()
        resp = client.market.save_market_information(request)
        assert isinstance(resp, ApiSaveMarketInformationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/market/information/save"
    finally:
        client.close()


@respx.mock
def test_save_market_information_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/market/information/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = SaveMarketInformationRequestDTO.model_construct()
            resp = await client.market.save_market_information(request)
            assert isinstance(resp, ApiSaveMarketInformationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
