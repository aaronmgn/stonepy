from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiTradeOrderResponseDTO, NewStopLimitOrderRequestDTO

_RESPONSE_BODY = '{"Status":2,"StatusReason":1,"OrderId":1,"Orders":[{"OrderId":1,"StatusReason":1,"Status":1,"OrderTypeId":1,"Price":"1.23","Quantity":"1.23","TriggerPrice":"1.23","CommissionCharge":"1.23","IfDone":null,"GuaranteedPremium":"1.23","OCO":null,"AssociatedOrders":null,"Associated":false}],"Quote":{"QuoteId":1,"Status":1,"StatusReason":1},"Actions":[{"ActionedOrderId":1,"ActioningOrderId":1,"Quantity":"1.23","ProfitAndLoss":"1.23","ProfitAndLossCurrency":"x","OrderActionTypeId":1}],"ErrorMessage":"x"}'  # noqa: E501


@respx.mock
def test_place_order_returns_response() -> None:
    route = respx.post("https://api.example/order/newstoplimitorder").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = NewStopLimitOrderRequestDTO.model_construct()
        resp = client.order.place_order(request)
        assert isinstance(resp, ApiTradeOrderResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/order/newstoplimitorder"
    finally:
        client.close()


@respx.mock
def test_place_order_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/order/newstoplimitorder").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = NewStopLimitOrderRequestDTO.model_construct()
            resp = await client.order.place_order(request)
            assert isinstance(resp, ApiTradeOrderResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
