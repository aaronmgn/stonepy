from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import DeleteAllocationProfileRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_delete_allocation_profile_returns_response() -> None:
    respx.post("https://api.example/tradingadvisor/allocationprofile/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = DeleteAllocationProfileRequestDTO.model_construct()
        resp = client.tradingadvisor.delete_allocation_profile(request)
        assert resp is not None
    finally:
        client.close()
