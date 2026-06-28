from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_followers_returns_response() -> None:
    respx.get("https://api.example/useraccount/followers").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        screen_names = "x"
        resp = client.user_account.list_followers(screen_names)
        assert resp is not None
    finally:
        client.close()
