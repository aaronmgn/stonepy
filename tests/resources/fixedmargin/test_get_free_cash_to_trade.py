from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_free_cash_to_trade_returns_response() -> None:
    respx.get("https://api.example/fixedmargin/freecashtotrade/get").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        resp = client.fixedmargin.get_free_cash_to_trade()
        assert resp is not None
    finally:
        client.close()
