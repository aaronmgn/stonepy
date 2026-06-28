from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import OrderHistoryDTO

_RESPONSE_BODY = '{"MarketId":1,"MarketName":"x","DirectionId":"x","OriginalQuantity":"1.23","TriggerPrice":"1.23","ExpiryTypeId":1,"StatusId":1,"OrderTypeId":1,"CurrencyId":1,"OrderId":1,"FilledQuantity":"1.23","ClientAccountId":1,"ExecutionPolicyId":1,"FillLevel":"1.23"}'  # noqa: E501


@respx.mock
def test_get_order_history_returns_response() -> None:
    route = respx.get("https://api.example/order/v2/orderhistory").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        resp = client.order.get_order_history(
            client_account_id,
            start_date_time=1,
            end_date_time=1,
            page_size=1,
            page=1,
        )
        assert isinstance(resp, OrderHistoryDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/v2/orderhistory"
    finally:
        client.close()


@respx.mock
def test_get_order_history_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/v2/orderhistory").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            resp = await client.order.get_order_history(
                client_account_id,
                start_date_time=1,
                end_date_time=1,
                page_size=1,
                page=1,
            )
            assert isinstance(resp, OrderHistoryDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
