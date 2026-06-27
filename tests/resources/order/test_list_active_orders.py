from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListActiveOrdersRequestDTO, ListActiveOrdersResponseDTO

_RESPONSE_BODY = '{"ActiveOrders":[{"TradeOrder":{"ManagedTrades":[{"OrderId":1,"Quantity":"1.23","TradingAccountId":1,"TradingAccountCode":"x","TradingAccountName":"x","LastChangedDateTimeUTC":"/Date(1577836800000)/"}],"CreatedDateTimeUTC":"/Date(1577836800000)/","SpreadCost":"1.23","Commission":"1.23"},"StopLimitOrder":{"Guaranteed":false,"TriggerPrice":"1.23","ExpiryDateTimeUTC":"/Date(1577836800000)/","Applicability":"x","ParentOrderId":1,"TrailingDistance":"1.23","Associated":false,"TriggerLevelCalculationTypeId":1,"TriggerLevelCalculationValue":"1.23"},"TypeId":1}]}'  # noqa: E501


@respx.mock
def test_list_active_orders_returns_response() -> None:
    route = respx.post("https://api.example/order/activeorders").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request_dto = ListActiveOrdersRequestDTO.model_construct()
        resp = client.order.list_active_orders(request_dto)
        assert isinstance(resp, ListActiveOrdersResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/order/activeorders"
    finally:
        client.close()


@respx.mock
def test_list_active_orders_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/order/activeorders").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request_dto = ListActiveOrdersRequestDTO.model_construct()
            resp = await client.order.list_active_orders(request_dto)
            assert isinstance(resp, ListActiveOrdersResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
