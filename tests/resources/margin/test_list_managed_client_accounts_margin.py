from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_list_managed_client_accounts_margin_returns_response() -> None:
    respx.get("https://api.example/margin/ManagedClientAccountsMargin").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        resp = client.margin.list_managed_client_accounts_margin()
        assert resp is not None
    finally:
        client.close()
