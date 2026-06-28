from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_order_history_returns_response() -> None:
    respx.get("https://api.example/order/v2/orderhistory").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client_account_id = 1
        start_date_time = 1
        end_date_time = 1
        page_size = 1
        page = 1
        resp = client.order.get_order_history(
            client_account_id,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            page_size=page_size,
            page=page,
        )
        assert resp is not None
    finally:
        client.close()
