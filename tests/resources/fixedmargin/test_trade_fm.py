from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import NewFixedMarginTradeOrderRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_trade_fm_returns_response() -> None:
    respx.post("https://api.example/fixedmargin/newtradeorder").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = NewFixedMarginTradeOrderRequestDTO.model_construct()
        resp = client.fixedmargin.trade_fm(request)
        assert resp is not None
    finally:
        client.close()
