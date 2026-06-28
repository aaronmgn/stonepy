from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import UpdateFixedMarginTradeOrderRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_update_trade_fm_returns_response() -> None:
    respx.post("https://api.example/fixedmargin/updatetradeorder").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = UpdateFixedMarginTradeOrderRequestDTO.model_construct()
        resp = client.fixedmargin.update_trade_fm(request)
        assert resp is not None
    finally:
        client.close()
