from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import UpdateTradeOrderRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_simulate_update_trade_returns_response() -> None:
    respx.post("https://api.example/order/simulate/updatetradeorder").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = UpdateTradeOrderRequestDTO.model_construct()
        resp = client.order.simulate_update_trade(request)
        assert resp is not None
    finally:
        client.close()
