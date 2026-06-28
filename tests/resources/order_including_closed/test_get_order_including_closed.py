from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_order_including_closed_returns_response() -> None:
    respx.get("https://api.example/orderIncludingClosed/v2/orderIncludingClosed/1").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        order_id = 1
        client_account_id = 1
        resp = client.order_including_closed.get_order_including_closed(order_id, client_account_id)
        assert resp is not None
    finally:
        client.close()
