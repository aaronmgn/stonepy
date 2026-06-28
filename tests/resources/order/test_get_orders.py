from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import EnrichedOrderDTO

_RESPONSE_BODY = '{"MarketId":1,"MarketName":"x","OrderDirectionId":1,"OrderTypeId":1,"Quantity":"1.23","Level":"1.23","OrderExpiryId":1,"ExpiryDateTimeUtc":"/Date(1577836800000)/","OrderId":1,"StatusId":1,"CurrencyId":1,"RequestId":"x","ClientAccountId":1,"Tax":"1.23","Commission":"1.23","OrderReasonId":1,"ReasonText":"x","ExecutionPolicyId":1,"TransactionId":"x","FxConversionCharge":"1.23","FillLevel":"1.23","RequestTypeId":1,"Version":1,"OrderValue":"1.23","TotalValue":"1.23","LastChangedDateTimeUtc":"/Date(1577836800000)/"}'  # noqa: E501


@respx.mock
def test_get_orders_returns_response() -> None:
    route = respx.get("https://api.example/order/v2/orders").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = "1"
        resp = client.order.get_orders(client_account_id, limit=1)
        assert isinstance(resp, EnrichedOrderDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/v2/orders"
    finally:
        client.close()


@respx.mock
def test_get_orders_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/v2/orders").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = "1"
            resp = await client.order.get_orders(client_account_id, limit=1)
            assert isinstance(resp, EnrichedOrderDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
