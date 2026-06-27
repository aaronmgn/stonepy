from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListTradeHistoryResponseDTO

_RESPONSE_BODY = '{"TradeHistory":[{"OrderId":1,"OpeningOrderIds":[],"MarketId":1,"MarketName":"x","Direction":"x","OriginalQuantity":"1.23","Quantity":"1.23","Price":"1.23","TradingAccountId":1,"Currency":"x","RealisedPnl":"1.23","RealisedPnlCurrency":"x","LastChangedDateTimeUtc":"/Date(1577836800000)/","ExecutedDateTimeUtc":"/Date(1577836800000)/","TradeReference":"x","ManagedTrades":[],"OrderReference":"x","Source":"x","IsCloseBy":false,"Liquidation":false,"FixedInitialMargin":"1.23"}],"SupplementalOpenOrders":[{"OrderId":1,"OpeningOrderIds":[],"MarketId":1,"MarketName":"x","Direction":"x","OriginalQuantity":"1.23","Quantity":"1.23","Price":"1.23","TradingAccountId":1,"Currency":"x","RealisedPnl":"1.23","RealisedPnlCurrency":"x","LastChangedDateTimeUtc":"/Date(1577836800000)/","ExecutedDateTimeUtc":"/Date(1577836800000)/","TradeReference":"x","ManagedTrades":[],"OrderReference":"x","Source":"x","IsCloseBy":false,"Liquidation":false,"FixedInitialMargin":"1.23"}]}'  # noqa: E501


@respx.mock
def test_list_trade_history_returns_response() -> None:
    route = respx.get("https://api.example/order/tradehistory").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        trading_account_id = 1
        max_results = 1
        from_ = 1
        resp = client.order.list_trade_history(
            trading_account_id=trading_account_id, max_results=max_results, from_=from_
        )
        assert isinstance(resp, ListTradeHistoryResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/order/tradehistory"
    finally:
        client.close()


@respx.mock
def test_list_trade_history_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/order/tradehistory").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            trading_account_id = 1
            max_results = 1
            from_ = 1
            resp = await client.order.list_trade_history(
                trading_account_id=trading_account_id, max_results=max_results, from_=from_
            )
            assert isinstance(resp, ListTradeHistoryResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
