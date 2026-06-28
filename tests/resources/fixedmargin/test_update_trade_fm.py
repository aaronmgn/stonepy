from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import FixedMarginOrderResponseDTO, UpdateFixedMarginTradeOrderRequestDTO

_RESPONSE_BODY = '{"InstructionStatusId":1,"InstructionStatusReasonId":1,"OrderStatusId":1,"OrderStatusReasonId":1,"OrderId":1,"Quantity":"1.23","ExecutionPrice":"1.23","FixedInitialMargin":"1.23","TakeProfitPrice":"1.23","StopLossPrice":"1.23","ErrorMessage":"x"}'  # noqa: E501


@respx.mock
def test_update_trade_fm_returns_response() -> None:
    route = respx.post("https://api.example/fixedmargin/updatetradeorder").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = UpdateFixedMarginTradeOrderRequestDTO.model_construct()
        resp = client.fixedmargin.update_trade_fm(request)
        assert isinstance(resp, FixedMarginOrderResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/fixedmargin/updatetradeorder"
    finally:
        client.close()


@respx.mock
def test_update_trade_fm_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/fixedmargin/updatetradeorder").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = UpdateFixedMarginTradeOrderRequestDTO.model_construct()
            resp = await client.fixedmargin.update_trade_fm(request)
            assert isinstance(resp, FixedMarginOrderResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
