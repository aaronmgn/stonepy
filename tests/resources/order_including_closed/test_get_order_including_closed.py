from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SingleActiveStopLimitOrderResponseDTO

_RESPONSE_BODY = '{"ActiveStopLimitOrder":{"OrderId":1,"ParentOrderId":1,"MarketId":1,"MarketName":"x","Direction":"x","Qauantity":"1.23","TriggerPrice":"1.23","TradingAccountId":1,"Type":1,"Applicability":1,"ExpiryDateTimeUTC":"/Date(1577836800000)/","Currency":"x","Status":1,"CreatedDateTimeUTC":"/Date(1577836800000)/","AutoRollover":false,"Guaranteed":false,"Associated":false}}'  # noqa: E501


@respx.mock
def test_get_order_including_closed_returns_response() -> None:
    route = respx.get("https://api.example/orderIncludingClosed/v2/orderIncludingClosed/1").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        order_id = 1
        client_account_id = 1
        resp = client.order_including_closed.get_order_including_closed(order_id, client_account_id)
        assert isinstance(resp, SingleActiveStopLimitOrderResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/orderIncludingClosed/v2/orderIncludingClosed/1"
        assert dict(route.calls[0].request.url.params) == {"clientAccountId": "1"}
    finally:
        client.close()


@respx.mock
def test_get_order_including_closed_async() -> None:
    async def run() -> None:
        route = respx.get(
            "https://api.example/orderIncludingClosed/v2/orderIncludingClosed/1"
        ).mock(return_value=httpx.Response(200, content=_RESPONSE_BODY))
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            order_id = 1
            client_account_id = 1
            resp = await client.order_including_closed.get_order_including_closed(
                order_id, client_account_id
            )
            assert isinstance(resp, SingleActiveStopLimitOrderResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            assert dict(route.calls[0].request.url.params) == {"clientAccountId": "1"}
        finally:
            await client.aclose()

    asyncio.run(run())
