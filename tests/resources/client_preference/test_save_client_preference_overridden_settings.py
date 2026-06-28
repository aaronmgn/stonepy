from __future__ import annotations

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient
from stonepy.models import ApiClientPreferencesOverriddenSettingsSaveRequestDTO


@pytest.mark.skip("Fill request values and response payload before enabling.")
@respx.mock
def test_save_client_preference_overridden_settings_returns_response() -> None:
    respx.post(
        "https://api.example/clientPreference/v2/clientPreference/overriddenSettings/save"
    ).mock(return_value=httpx.Response(200, json={}))
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        api_client_preferences_overridden_settings_save_request_dto = (
            ApiClientPreferencesOverriddenSettingsSaveRequestDTO.model_construct()
        )
        resp = client.client_preference.save_client_preference_overridden_settings(
            api_client_preferences_overridden_settings_save_request_dto
        )
        assert resp is not None
    finally:
        client.close()
