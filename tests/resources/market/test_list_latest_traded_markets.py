from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_latest_traded_markets_returns_response() -> None:
    respx.get("https://api.example/market/latesttraded").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        screen_names: list[str] = []
        number_of_results = 1
        resp = client.market.list_latest_traded_markets(screen_names, number_of_results)
        assert resp is not None
    finally:
        client.close()
