from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetOpenPositionResponseDTOv2

_RESPONSE_BODY = '{"OpenPosition":{"OrderId":1,"MarketId":1,"MarketName":"x","Direction":"x","Qauantity":"1.23","TriggerPrice":"1.23","TradingAccountId":1,"Currency":"x","Status":1,"StopOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"LimitOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"LastChangedDateTimeUTC":"/Date(1577836800000)/","CreatedDateTimeUTC":"/Date(1577836800000)/","ExecutedDateTimeUTC":"/Date(1577836800000)/","AutoRollover":false,"TradeReference":"x","ManagedTrades":[{"OrderId":1,"Quantity":"1.23","TradingAccountId":1,"TradingAccountCode":"x","TradingAccountName":"x","LastChangedDateTimeUTC":"/Date(1577836800000)/"}],"AllocationProfileId":1,"AllocationProfileName":"x","AssociatedOrders":{"Stop":{"Guaranteed":false,"TriggerPrice":"1.23","ExpiryDateTimeUTC":"/Date(1577836800000)/","Applicability":"x","ParentOrderId":1,"TrailingDistance":"1.23","Associated":false,"TriggerLevelCalculationTypeId":1,"TriggerLevelCalculationValue":"1.23"},"Limit":{"Guaranteed":false,"TriggerPrice":"1.23","ExpiryDateTimeUTC":"/Date(1577836800000)/","Applicability":"x","ParentOrderId":1,"TrailingDistance":"1.23","Associated":false,"TriggerLevelCalculationTypeId":1,"TriggerLevelCalculationValue":"1.23"}},"FixedInitialMargin":"1.23","PositionMethodId":1}}'  # noqa: E501


@respx.mock
def test_get_open_position_returns_response() -> None:
    route = respx.get("https://api.example/order/x/openposition").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        order_id = "x"
        resp = client.order.get_open_position(order_id)
        assert isinstance(resp, GetOpenPositionResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/x/openposition"
    finally:
        client.close()


@respx.mock
def test_get_open_position_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/x/openposition").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            order_id = "x"
            resp = await client.order.get_open_position(order_id)
            assert isinstance(resp, GetOpenPositionResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
