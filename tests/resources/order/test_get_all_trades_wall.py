from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_all_trades_wall_returns_response() -> None:
    respx.get("https://api.example/order/getalltradeswallinfo").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        direction = "x"
        number_of_results = 1
        resp = client.order.get_all_trades_wall(direction, number_of_results)
        assert resp is not None
    finally:
        client.close()
