from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListStopLimitOrderHistoryResponseDTO

_RESPONSE_BODY = '{"StopLimitOrderHistory":[{"OrderId":1,"MarketId":1,"MarketName":"x","Direction":"x","OriginalQuantity":"1.23","Price":"1.23","TriggerPrice":"1.23","TrailingDistance":"1.23","TradingAccountId":1,"TypeId":1,"OrderApplicabilityId":1,"Currency":"x","StatusId":1,"LastChangedDateTimeUtc":"/Date(1577836800000)/","CreatedDateTimeUtc":"/Date(1577836800000)/","Guaranteed":false,"TradeReference":"x","OrderReference":"x","Source":"x"}]}'  # noqa: E501


@respx.mock
def test_list_stop_limit_order_history_returns_response() -> None:
    route = respx.get("https://api.example/order/stoplimitorderhistory").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        trading_account_id = 1
        max_results = 1
        from_ = 1
        resp = client.order.list_stop_limit_order_history(
            trading_account_id=trading_account_id, max_results=max_results, from_=from_
        )
        assert isinstance(resp, ListStopLimitOrderHistoryResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/stoplimitorderhistory"
    finally:
        client.close()


@respx.mock
def test_list_stop_limit_order_history_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/stoplimitorderhistory").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            trading_account_id = 1
            max_results = 1
            from_ = 1
            resp = await client.order.list_stop_limit_order_history(
                trading_account_id=trading_account_id, max_results=max_results, from_=from_
            )
            assert isinstance(resp, ListStopLimitOrderHistoryResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
