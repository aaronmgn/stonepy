from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SignalPerformanceResponseDTO

_RESPONSE_BODY = '{"Wins":1,"Losses":1,"TopPerformers":[{"SignalId":1,"MarketName":"x","Percentage":"1.23","ExpirationDateTime":"/Date(1577836800000)/","TradeType":1,"PnL":"1.23","Hot":false}],"BottomPerformers":[{"SignalId":1,"MarketName":"x","Percentage":"1.23","ExpirationDateTime":"/Date(1577836800000)/","TradeType":1,"PnL":"1.23","Hot":false}]}'  # noqa: E501


@respx.mock
def test_get_signal_performance_returns_response() -> None:
    route = respx.get("https://api.example/pm/signals/performance").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.pm.get_signal_performance()
        assert isinstance(resp, SignalPerformanceResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pm/signals/performance"
    finally:
        client.close()


@respx.mock
def test_get_signal_performance_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pm/signals/performance").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.pm.get_signal_performance()
            assert isinstance(resp, SignalPerformanceResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
