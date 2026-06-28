from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_changed_orders_returns_response() -> None:
    respx.get("https://api.example/order/changedorders").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        trading_account_id = 1
        from_ = 1
        resp = client.order.get_changed_orders(trading_account_id, from_)
        assert resp is not None
    finally:
        client.close()
