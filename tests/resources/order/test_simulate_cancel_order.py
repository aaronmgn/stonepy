from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import CancelOrderRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_simulate_cancel_order_returns_response() -> None:
    respx.post("https://api.example/order/simulate/cancel").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = CancelOrderRequestDTO.model_construct()
        resp = client.order.simulate_cancel_order(request)
        assert resp is not None
    finally:
        client.close()
