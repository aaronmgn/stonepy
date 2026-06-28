from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_multiple_users_details_by_facebook_ids_returns_response() -> None:
    respx.get("https://api.example/useraccount/getusersbyfacebookids").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        resp = client.user_account.get_multiple_users_details_by_facebook_ids()
        assert resp is not None
    finally:
        client.close()
