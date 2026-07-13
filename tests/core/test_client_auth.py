from __future__ import annotations

import httpx
import pytest
import respx

from stonepy import AuthenticationError, ConfigurationError
from stonepy._core.config import ClientConfig
from stonepy.client import StoneXClient


@respx.mock
def test_credential_less_auth_refresh_raises_configuration_error() -> None:
    respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(401, content="{}")
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        with pytest.raises(ConfigurationError):
            client.client_preference.get_client_preferences_list(["x"], 1)
    finally:
        client.close()


@respx.mock
def test_config_credential_logon_with_empty_session_raises() -> None:
    respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(200, content='{"StatusCode":1}')
    )
    respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(401, content="{}")
    )
    config = ClientConfig(base_url="https://api.example", app_key="k", username="me", password="pw")
    client = StoneXClient(config)
    try:
        with pytest.raises(AuthenticationError):
            client.client_preference.get_client_preferences_list(["x"], 1)
    finally:
        client.close()
