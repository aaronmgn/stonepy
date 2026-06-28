from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_client_preferences_key_list_returns_response() -> None:
    respx.get("https://api.example/clientPreference/v2/clientPreference/keyList").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client_account_id = 1
        resp = client.client_preference.get_client_preferences_key_list(client_account_id)
        assert resp is not None
    finally:
        client.close()
