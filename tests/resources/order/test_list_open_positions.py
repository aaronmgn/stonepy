from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListOpenPositionsResponseDTO

_RESPONSE_BODY = '{"OpenPositions":[{"OrderId":1,"MarketId":1,"MarketName":"x","Direction":"x","Qauantity":"1.23","TriggerPrice":"1.23","TradingAccountId":1,"Currency":"x","Status":1,"StopOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"LimitOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"LastChangedDateTimeUTC":"/Date(1577836800000)/","CreatedDateTimeUTC":"/Date(1577836800000)/","ExecutedDateTimeUTC":"/Date(1577836800000)/","AutoRollover":false,"TradeReference":"x","ManagedTrades":[{"OrderId":1,"Quantity":"1.23","TradingAccountId":1,"TradingAccountCode":"x","TradingAccountName":"x","LastChangedDateTimeUTC":"/Date(1577836800000)/"}],"AllocationProfileId":1,"AllocationProfileName":"x","AssociatedOrders":{"Stop":{"Guaranteed":false,"TriggerPrice":"1.23","ExpiryDateTimeUTC":"/Date(1577836800000)/","Applicability":"x","ParentOrderId":1,"TrailingDistance":"1.23","Associated":false,"TriggerLevelCalculationTypeId":1,"TriggerLevelCalculationValue":"1.23"},"Limit":{"Guaranteed":false,"TriggerPrice":"1.23","ExpiryDateTimeUTC":"/Date(1577836800000)/","Applicability":"x","ParentOrderId":1,"TrailingDistance":"1.23","Associated":false,"TriggerLevelCalculationTypeId":1,"TriggerLevelCalculationValue":"1.23"}},"FixedInitialMargin":"1.23","PositionMethodId":1}]}'  # noqa: E501


@respx.mock
def test_list_open_positions_returns_response() -> None:
    route = respx.get("https://api.example/order/openpositions").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        trading_account_id = 1
        resp = client.order.list_open_positions(trading_account_id=trading_account_id)
        assert isinstance(resp, ListOpenPositionsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/openpositions"
    finally:
        client.close()


@respx.mock
def test_list_open_positions_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/openpositions").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            trading_account_id = 1
            resp = await client.order.list_open_positions(trading_account_id=trading_account_id)
            assert isinstance(resp, ListOpenPositionsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
