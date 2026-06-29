from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListProductInformationDTO, ListProductInformationResponseDTO

_RESPONSE_BODY = '{"ProductInformation":[{"MarketId":1,"MarketName":"x","MobileShortName":"x","MinimumSpread":"1.23","MinimumSpreadTimeUtc":"/Date(1577836800000)/","AdditionalMarketSpreads":[{"SpreadTimeUtc":"/Date(1577836800000)/","Spread":"1.23","SpreadUnits":1}],"MinimumMargin":"1.23","Bands":[{"LowerBound":"1.23","MarginFactor":"1.23"}],"Market24H":false,"TradingStartTimeUtc":"/Date(1577836800000)/","TradingEndTimeUtc":"/Date(1577836800000)/","BetPer":"1.23","ExpiryUtc":"/Date(1577836800000)/","MinStopDistance":"1.23","GuaranteedOrderMinDistance":"1.23","CurrencyId":1,"CurrencyIsoCode":"x","MarketUnderlyingType":"x","PriceDecimalPlaces":1,"MaxSize":"1.23","WebMinSize":"1.23","PhoneMinSize":"1.23","MarketTimeZoneOffsetMinutes":1}]}'  # noqa: E501


@respx.mock
def test_save_product_information_returns_response() -> None:
    route = respx.post("https://api.example/v2/market/productInformation").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ListProductInformationDTO.model_construct()
        resp = client.market.save_product_information(request)
        assert isinstance(resp, ListProductInformationResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/market/productInformation"
    finally:
        client.close()


@respx.mock
def test_save_product_information_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/market/productInformation").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ListProductInformationDTO.model_construct()
            resp = await client.market.save_product_information(request)
            assert isinstance(resp, ListProductInformationResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
