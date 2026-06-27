"""Resource-level coverage of the business-status rejection branch.

The generated happy-path tests always return an accepted Status (=2); this exercises the
complementary path where the default status decoder maps the response Status to a rejection and the
pipeline raises ``OrderRejectedError`` through the public client method.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.errors import OrderRejectedError
from stonepy.client import StoneXClient
from stonepy.models import ApiSimulateTradeOrderResponseDTO, NewTradeOrderRequestDTO


def _body(status: int, status_reason: int) -> str:
    return (
        f'{{"Status":{status},"StatusReason":{status_reason},"SimulatedCash":"1.23",'
        '"ActualCash":"1.23","SimulatedTotalMarginRequirement":"1.23",'
        '"ActualTotalMarginRequirement":"1.23","CurrencyId":1,'
        '"Orders":[{"StatusReason":1,"Status":1}],"Adjust":"1.23"}'
    )


# A fully-valid ApiSimulateTradeOrderResponseDTO whose top-level Status (5 = Rejected) the default
# decoder maps to a rejection. The body must validate first so the pipeline reaches the
# business-status check.
_REJECTION_BODY = _body(5, 42)


@respx.mock
def test_simulate_trade_rejection_raises_order_rejected_error() -> None:
    respx.post("https://api.example/order/simulate/newtradeorder").mock(
        return_value=httpx.Response(200, content=_REJECTION_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        with pytest.raises(OrderRejectedError) as excinfo:
            client.order.simulate_trade(NewTradeOrderRequestDTO.model_construct())
        assert excinfo.value.status == 5
        assert excinfo.value.status_reason == 42
    finally:
        client.close()


@respx.mock
def test_simulate_trade_open_status_is_not_rejected() -> None:
    # Status 3 (Open) is a normal non-rejection outcome: the parsed response is returned, not
    # raised. Guards the previous bug where any Status != 2 (Accepted) raised OrderRejectedError.
    respx.post("https://api.example/order/simulate/newtradeorder").mock(
        return_value=httpx.Response(200, content=_body(3, 1))
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.order.simulate_trade(NewTradeOrderRequestDTO.model_construct())
        assert isinstance(resp, ApiSimulateTradeOrderResponseDTO)
        assert resp.status == 3
    finally:
        client.close()
