from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import SaveAllocationProfileRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_save_allocation_profile_returns_response() -> None:
    respx.post("https://api.example/tradingadvisor/allocationprofile/save").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = SaveAllocationProfileRequestDTO.model_construct()
        resp = client.tradingadvisor.save_allocation_profile(request)
        assert resp is not None
    finally:
        client.close()
