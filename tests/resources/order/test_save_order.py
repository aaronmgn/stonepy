from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest
import respx

from stonepy import OrderRejectedError, OrderStatusUnknownError
from stonepy._core.codec import loads
from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ExecutionResponseDTO
from tests.resources.order._requests import MALFORMED_ACK_BODIES, valid_execution_venue_request

_RESPONSE_BODY = '{"RequestId":"x","Status":"Success","Reason":"x"}'


@respx.mock
def test_save_order_returns_response() -> None:
    route = respx.post("https://api.example/v2/order").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = valid_execution_venue_request()
        resp = client.order.save_order(request)
        assert isinstance(resp, ExecutionResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/order"
    finally:
        client.close()


@respx.mock
def test_save_order_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = valid_execution_venue_request()
            resp = await client.order.save_order(request)
            assert isinstance(resp, ExecutionResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_save_order_success_status_string_returns_model() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(200, content='{"RequestId":"r1","Status":"Success"}')
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            resp = client.order.save_order(valid_execution_venue_request())
            assert resp.status == "Success"
        finally:
            client.close()


def test_save_order_failure_status_string_raises_order_rejected() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(
                200, content='{"RequestId":"r1","Status":"Failure","Reason":"Insufficient funds"}'
            )
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            with pytest.raises(OrderRejectedError) as exc_info:
                client.order.save_order(valid_execution_venue_request())
            assert exc_info.value.reason == "Insufficient funds"
        finally:
            client.close()


def test_save_order_unknown_text_status_raises_indeterminate_error() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(
                200, content='{"RequestId":"r1","Status":"Queued","Reason":"Pending venue"}'
            )
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            with pytest.raises(OrderStatusUnknownError) as exc_info:
                client.order.save_order(valid_execution_venue_request())
            assert exc_info.value.status == "Queued"
            assert exc_info.value.method == "POST"
            assert exc_info.value.path == "/v2/order"
        finally:
            client.close()


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_save_order_wire_body_matches_validated_request(asynchronous: bool) -> None:
    route = respx.post("https://api.example/v2/order").respond(200, content=_RESPONSE_BODY)
    request = valid_execution_venue_request()

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "alice")
            await client.order.save_order(request)

    if asynchronous:
        asyncio.run(run())
    else:
        with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
            client._ctx.session.set_token("TOKEN", "alice")
            client.order.save_order(request)
    body = loads(route.calls[0].request.content)
    assert body["MarketId"] == 456
    assert body["TradingAccountId"] == 123
    assert body["ClientAccountId"] == 789
    assert body["Bid"] == Decimal("123.456789123456789")
    assert body["Ask"] == Decimal("123.456789123456799")
    assert len(body["OrderRequests"]) == 2
    parent, stop = body["OrderRequests"]
    assert parent["MarketId"] == stop["MarketId"] == 456
    assert parent["TradingAccountId"] == stop["TradingAccountId"] == 123
    assert parent["OrderDirectionId"] == 1 and stop["OrderDirectionId"] == 2
    assert parent["Quantity"] == stop["Quantity"] == Decimal("1.23456789123456789")
    assert parent["Level"] == Decimal("123.456789123456799")
    assert stop["Level"] == Decimal("120.123456789123456789")
    assert stop["ParentOrderRequestToken"] == parent["OrderRequestToken"] == "parent"


@pytest.mark.parametrize("body", MALFORMED_ACK_BODIES)
@respx.mock
def test_sync_save_order_malformed_status_is_indeterminate(body: bytes) -> None:
    route = respx.post("https://api.example/v2/order").respond(200, content=body)
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        client._ctx.session.set_token("TOKEN", "alice")
        with pytest.raises(OrderStatusUnknownError):
            client.order.save_order(valid_execution_venue_request())
    assert route.call_count == 1


@pytest.mark.parametrize("body", MALFORMED_ACK_BODIES)
@respx.mock
def test_async_save_order_malformed_status_is_indeterminate(body: bytes) -> None:
    route = respx.post("https://api.example/v2/order").respond(200, content=body)

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "alice")
            with pytest.raises(OrderStatusUnknownError):
                await client.order.save_order(valid_execution_venue_request())

    asyncio.run(run())
    assert route.call_count == 1
