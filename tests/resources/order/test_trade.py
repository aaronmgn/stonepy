from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest
import respx

from stonepy import OrderStatusUnknownError
from stonepy._core.codec import loads
from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiTradeOrderResponseDTO
from tests.resources.order._requests import MALFORMED_ACK_BODIES, valid_trade_request

_RESPONSE_BODY = '{"Status":1,"StatusReason":1,"OrderId":1,"Orders":[{"OrderId":1,"StatusReason":1,"Status":1,"OrderTypeId":1,"Price":"1.23","Quantity":"1.23","TriggerPrice":"1.23","CommissionCharge":"1.23","IfDone":null,"GuaranteedPremium":"1.23","OCO":null,"AssociatedOrders":null,"Associated":false}],"Quote":{"QuoteId":1,"Status":1,"StatusReason":1},"Actions":[{"ActionedOrderId":1,"ActioningOrderId":1,"Quantity":"1.23","ProfitAndLoss":"1.23","ProfitAndLossCurrency":"x","OrderActionTypeId":1}],"ErrorMessage":"x"}'  # noqa: E501


@respx.mock
def test_trade_returns_response() -> None:
    route = respx.post("https://api.example/order/newtradeorder").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = valid_trade_request()
        resp = client.order.trade(request)
        assert isinstance(resp, ApiTradeOrderResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/order/newtradeorder"
    finally:
        client.close()


@respx.mock
def test_trade_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/order/newtradeorder").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = valid_trade_request()
            resp = await client.order.trade(request)
            assert isinstance(resp, ApiTradeOrderResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_trade_wire_body_matches_validated_request(asynchronous: bool) -> None:
    route = respx.post("https://api.example/order/newtradeorder").respond(
        200, content=_RESPONSE_BODY
    )
    request = valid_trade_request()

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "alice")
            await client.order.trade(request)

    if asynchronous:
        asyncio.run(run())
    else:
        with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
            client._ctx.session.set_token("TOKEN", "alice")
            client.order.trade(request)
    body = loads(route.calls[0].request.content)
    assert body["MarketId"] == 456
    assert body["TradingAccountId"] == 123
    assert body["Direction"] == "Buy"
    assert body["Currency"] == "USD"
    assert body["Quantity"] == Decimal("1.23456789123456789")
    assert body["BidPrice"] == Decimal("123.456789123456789")
    assert body["OfferPrice"] == Decimal("123.456789123456799")
    assert body["IfDone"] == [
        {
            "Stop": {
                "Guaranteed": False,
                "TriggerPrice": Decimal("120.123456789123456789"),
                "Applicability": "GTC",
            }
        }
    ]


@pytest.mark.parametrize("body", MALFORMED_ACK_BODIES)
@respx.mock
def test_sync_trade_malformed_status_is_indeterminate(body: bytes) -> None:
    route = respx.post("https://api.example/order/newtradeorder").respond(200, content=body)
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        client._ctx.session.set_token("TOKEN", "alice")
        with pytest.raises(OrderStatusUnknownError):
            client.order.trade(valid_trade_request())
    assert route.call_count == 1


@pytest.mark.parametrize("body", MALFORMED_ACK_BODIES)
@respx.mock
def test_async_trade_malformed_status_is_indeterminate(body: bytes) -> None:
    route = respx.post("https://api.example/order/newtradeorder").respond(200, content=body)

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "alice")
            with pytest.raises(OrderStatusUnknownError):
                await client.order.trade(valid_trade_request())

    asyncio.run(run())
    assert route.call_count == 1
