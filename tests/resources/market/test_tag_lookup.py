from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_tag_lookup_returns_response() -> None:
    respx.get("https://api.example/market/v2/market/tagLookup").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client_account_id = "x"
        resp = client.market.tag_lookup(client_account_id)
        assert resp is not None
    finally:
        client.close()
