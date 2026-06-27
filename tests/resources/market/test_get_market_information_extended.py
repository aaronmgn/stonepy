from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiGetMarketInformationExtendedResponseDTOv2

_RESPONSE_BODY = '{"MarketInformation":{"PriceRuleSpecId":1,"PriceSourceId":1,"MarketCurrencyCode":"x","UnderlyingCurrencyCode":"x","IsBinaryMarket":false,"IsOptionsMarket":false,"IsRollingCashMarket":false,"IsDailyFundedTradeMarket":false,"BandedSpreads":[],"DefaultMarginFactor":"1.23","LastTradingUTC":"/Date(1577836800000)/","FxCommission":"1.23","FxCommissionQuantity":"1.23"}}'  # noqa: E501


@respx.mock
def test_get_market_information_extended_returns_response() -> None:
    route = respx.get("https://api.example/market/v2/market/1/informationExtended").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = 1
        client_account_id = 1
        resp = client.market.get_market_information_extended(market_id, client_account_id)
        assert isinstance(resp, ApiGetMarketInformationExtendedResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/market/v2/market/1/informationExtended"
    finally:
        client.close()


@respx.mock
def test_get_market_information_extended_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/market/v2/market/1/informationExtended").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = 1
            client_account_id = 1
            resp = await client.market.get_market_information_extended(market_id, client_account_id)
            assert isinstance(resp, ApiGetMarketInformationExtendedResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
