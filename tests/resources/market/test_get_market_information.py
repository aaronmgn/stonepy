from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetMarketInformationResponseDTOv2

_RESPONSE_BODY = '{"MarketInformation":{"MarketId":1,"ChartMarketId":1,"Name":"x","ExchangeId":1,"ExchangeName":"x","MarginFactor":"1.23","MinMarginFactor":"1.23","MarginFactorUnits":1,"MaxMarginFactor":"1.23","ClientMarginFactor":"1.23","MinDistance":"1.23","MinDistanceUnits":1,"WebMinSize":"1.23","MaxSize":"1.23","MarketSizesCurrencyCode":"x","MaxLongSize":"1.23","MaxShortSize":"1.23","Market24H":false,"PriceDecimalPlaces":1,"DefaultQuoteLength":1,"TradeOnWeb":false,"LimitUp":false,"LimitDown":false,"LongPositionOnly":false,"CloseOnly":false,"IncrementSize":"1.23","MarketEod":[{"MarketEodUnit":"x","MarketEodAmount":1}],"PriceTolerance":"1.23","ConvertPriceToPipsMultiplier":1,"MarketSettingsTypeId":1,"MarketSettingsType":"x","MobileShortName":"x","CentralClearingType":"x","CentralClearingTypeDescription":"x","MarketCurrencyId":1,"PhoneMinSize":"1.23","DailyFinancingAppliedAtUtc":"/Date(1577836800000)/","NextMarketEodTimeUtc":"/Date(1577836800000)/","TradingStartTimeUtc":"/Date(1577836800000)/","TradingEndTimeUtc":"/Date(1577836800000)/","MarketPricingTimes":[{"DayOfWeek":1,"StartTimeUtc":{"UtcDateTime":"/Date(1577836800000)/","OffsetMinutes":1},"EndTimeUtc":{"UtcDateTime":"/Date(1577836800000)/","OffsetMinutes":1}}],"MarketBreakTimes":[{"DayOfWeek":1,"StartTimeUtc":{"UtcDateTime":"/Date(1577836800000)/","OffsetMinutes":1},"EndTimeUtc":{"UtcDateTime":"/Date(1577836800000)/","OffsetMinutes":1}}],"MarketSpreads":{"SpreadTimeUtc":"/Date(1577836800000)/","Spread":"1.23","SpreadUnits":1},"GuaranteedOrderPremium":"1.23","GuaranteedOrderPremiumUnits":1,"GuaranteedOrderMinDistance":"1.23","GuaranteedOrderMinDistanceUnits":1,"PriceToleranceUnits":"1.23","MarketTimeZoneOffsetMinutes":1,"QuantityConversionFactor":"1.23","PointFactorDivisor":1,"BetPer":"1.23","MarketUnderlyingTypeId":1,"MarketUnderlyingType":"x","AllowGuaranteedOrders":false,"OrdersAwareMargining":false,"OrdersAwareMarginingMinimum":"1.23","CommissionChargeMinimum":"1.23","CommissionRate":"1.23","CommissionRateUnits":1,"ExpiryUtc":"/Date(1577836800000)/","StepMargin":{"EligibleForStepMargin":false,"StepMarginConfigured":false,"InheritedFromParentAccountOperator":false,"Bands":[]},"FutureRolloverUTC":"/Date(1577836800000)/","AllowRollover":false,"ExpiryBasisId":1,"ExpiryBasisText":"x","OptionTypeId":1,"OptionType":"x","StrikePrice":"1.23","MarketTypeId":1,"MarketType":"x","Weighting":1,"FxFinancing":{"CaptureDateTime":"/Date(1577836800000)/","LongPoints":"1.23","ShortPoints":"1.23","LongCharge":"1.23","ShortCharge":"1.23","Quantity":"1.23","ChargeCurrencyId":1,"DaysToRoll":1},"UnderlyingRicCode":"x","NewsUnderlyingOverrideType":"x","NewsUnderlyingOverrideCode":"x","TrailingStepConversionFactor":"1.23","IsDMA":false,"IsKnockout":false,"Knockout":{"PairedMarkets":1,"KnockoutLevels":1,"KnockoutIncrement":"1.23","KnockoutIncrementUnits":1,"KnockoutMinDistance":"1.23","KnockoutMinDistanceUnits":1},"CorporateActions":{"CorporateActionId":1},"Prices":{"BidPrice":"1.23","OfferPrice":"1.23","MarketState":[0]},"Identifiers":{"IdentifierCode":"x","Isin":"x","Sedol":"x"},"MarketUnderlyingId":1,"FullMarketName":"x"}}'  # noqa: E501


@respx.mock
def test_get_market_information_returns_response() -> None:
    route = respx.get("https://api.example/v2/market/x/information").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_id = "x"
        client_account_id = 1
        resp = client.market.get_market_information(market_id, client_account_id)
        assert isinstance(resp, GetMarketInformationResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/market/x/information"
        assert dict(route.calls[0].request.url.params) == {"clientAccountId": "1"}
    finally:
        client.close()


@respx.mock
def test_get_market_information_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/market/x/information").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_id = "x"
            client_account_id = 1
            resp = await client.market.get_market_information(market_id, client_account_id)
            assert isinstance(resp, GetMarketInformationResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {"clientAccountId": "1"}
        finally:
            await client.aclose()

    asyncio.run(run())
