from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_orders_by_reference_returns_response() -> None:
    respx.get("https://api.example/order/v2/order/orders/1").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        reference = "x"
        client_account_id = 1
        resp = client.order.get_orders_by_reference(reference, client_account_id)
        assert resp is not None
    finally:
        client.close()
