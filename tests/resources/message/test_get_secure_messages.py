from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_get_secure_messages_returns_response() -> None:
    respx.get("https://api.example/message/v2/message/SecureMessages").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        legal_party_id = 1
        client_account_id = "x"
        resp = client.message.get_secure_messages(legal_party_id, client_account_id)
        assert resp is not None
    finally:
        client.close()
