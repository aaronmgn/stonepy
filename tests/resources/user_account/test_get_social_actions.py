from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_social_actions_returns_response() -> None:
    respx.get("https://api.example/useraccount/getsocialactions").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        resp = client.user_account.get_social_actions()
        assert resp is not None
    finally:
        client.close()
