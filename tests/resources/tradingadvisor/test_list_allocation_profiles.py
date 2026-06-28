from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_allocation_profiles_returns_response() -> None:
    respx.get("https://api.example/tradingadvisor/allocationprofiles").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        trading_account_id = 1
        resp = client.tradingadvisor.list_allocation_profiles(trading_account_id)
        assert resp is not None
    finally:
        client.close()
