from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import GetActiveStopLimitOrderResponseDTOv2

_RESPONSE_BODY = '{"ActiveStopLimitOrder":{"OrderId":1,"ParentOrderId":1,"MarketId":1,"MarketName":"x","Direction":"x","Qauantity":"1.23","TriggerPrice":"1.23","TradingAccountId":1,"Type":1,"Applicability":1,"ExpiryDateTimeUTC":"/Date(1577836800000)/","Currency":"x","Status":1,"StopOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"LimitOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"OcoOrder":{"OrderId":1,"TriggerPrice":"1.23","TrailingDistance":"1.23","Quantity":"1.23","Guaranteed":false},"CreatedDateTimeUTC":"/Date(1577836800000)/","AutoRollover":false,"Guaranteed":false,"TradeReference":"x","AllocationProfileId":1,"AllocationProfileName":"x","Associated":false,"PositionMethodId":1}}'  # noqa: E501


# The v2 catalog path templates this endpoint as "/order/v2{orderId}/activeStopLimitOrder"
# with no slash before {orderId} (an upstream catalog quirk faithfully reproduced by the
# generator), so order_id=1 renders as "/order/v21/activeStopLimitOrder".
@respx.mock
def test_get_active_stop_limit_order_returns_response() -> None:
    route = respx.get("https://api.example/order/v21/activeStopLimitOrder").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        order_id = 1
        client_account_id = 1
        resp = client.order.get_active_stop_limit_order(order_id, client_account_id)
        assert isinstance(resp, GetActiveStopLimitOrderResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/v21/activeStopLimitOrder"
        assert dict(route.calls[0].request.url.params) == {"clientAccountId": "1"}
    finally:
        client.close()


@respx.mock
def test_get_active_stop_limit_order_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/v21/activeStopLimitOrder").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            order_id = 1
            client_account_id = 1
            resp = await client.order.get_active_stop_limit_order(order_id, client_account_id)
            assert isinstance(resp, GetActiveStopLimitOrderResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
