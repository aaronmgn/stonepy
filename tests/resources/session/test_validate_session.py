from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import ApiValidateSessionRequestDTOv2


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_validate_session_returns_response() -> None:
    respx.post("https://api.example/session/v2/Session/validate").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        request = ApiValidateSessionRequestDTOv2.model_construct()
        resp = client.session.validate_session(request)
        assert resp is not None
    finally:
        client.close()
