from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_username_returns_response() -> None:
    respx.get("https://api.example/useraccount/username").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        session_id = "x"
        client_account_id = 1
        resp = client.user_account.get_username(session_id, client_account_id)
        assert resp is not None
    finally:
        client.close()
