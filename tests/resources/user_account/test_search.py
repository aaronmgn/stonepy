from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_search_returns_response() -> None:
    respx.get("https://api.example/useraccount/search").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        page_number = 1
        resp = client.user_account.search(page_number)
        assert resp is not None
    finally:
        client.close()
