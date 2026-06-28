from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiSimulateTradeOrderResponseDTO, UpdateStopLimitOrderRequestDTO

_RESPONSE_BODY = '{"Status":1,"StatusReason":1,"SimulatedCash":"1.23","ActualCash":"1.23","SimulatedTotalMarginRequirement":"1.23","ActualTotalMarginRequirement":"1.23","CurrencyId":1,"Orders":[{"StatusReason":1,"Status":1}],"Adjust":"1.23"}'  # noqa: E501


@respx.mock
def test_simulate_update_order_returns_response() -> None:
    route = respx.post("https://api.example/order/simulate/updatestoplimitorder").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = UpdateStopLimitOrderRequestDTO.model_construct()
        resp = client.order.simulate_update_order(request)
        assert isinstance(resp, ApiSimulateTradeOrderResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/order/simulate/updatestoplimitorder"
    finally:
        client.close()


@respx.mock
def test_simulate_update_order_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/order/simulate/updatestoplimitorder").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = UpdateStopLimitOrderRequestDTO.model_construct()
            resp = await client.order.simulate_update_order(request)
            assert isinstance(resp, ApiSimulateTradeOrderResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
