from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_charting_enabled_returns_response() -> None:
    respx.get("https://api.example/useraccount/1/ChartingEnabled").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        id = "x"
        resp = client.user_account.get_charting_enabled(id)
        assert resp is not None
    finally:
        client.close()
