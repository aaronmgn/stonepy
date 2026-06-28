from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_pending_orders_returns_response() -> None:
    respx.get("https://api.example/pm/orders/pending").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        resp = client.pm.get_pending_orders()
        assert resp is not None
    finally:
        client.close()
