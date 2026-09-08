from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy import AuthenticationError, ConfigurationError
from stonepy._core.clock import FakeClock
from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiLogOnRequestDTO


def _logon_request() -> ApiLogOnRequestDTO:
    return ApiLogOnRequestDTO(
        UserName="me",
        Password="pw",
        AppKey="key",
        AppVersion="stonepy",
        AppComments="",
    )


def _logon_response(token: str) -> dict[str, object]:
    return {
        "Session": token,
        "PasswordChangeRequired": False,
        "AllowedAccountOperator": False,
        "StatusCode": 1,
        "Is2FAEnabled": False,
        "TwoFAToken": "",
        "Additional2FAMethods": [],
    }


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


@respx.mock
def test_manual_logon_installs_sync_proactive_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr("stonepy.client.SystemClock", lambda: clock)
    logon = respx.post("https://api.example/v2/session").mock(
        side_effect=[
            httpx.Response(200, json=_logon_response("MANUAL-TOKEN")),
            httpx.Response(200, json=_logon_response("REPLAY-TOKEN")),
        ]
    )
    protected = respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(200, json={"ClientPreferences": []})
    )
    client = StoneXClient(
        ClientConfig(base_url="https://api.example", proactive_refresh_seconds=10.0)
    )
    try:
        client.session.log_on(_logon_request())
        clock.advance(10.0)

        response = client.client_preference.get_client_preferences_list(["x"], 1)

        assert response.client_preferences == []
        assert len(logon.calls) == 2
        assert protected.calls[0].request.headers["Session"] == "REPLAY-TOKEN"
        assert protected.calls[0].request.headers["UserName"] == "me"
    finally:
        client.close()


@respx.mock
def test_manual_logon_installs_async_proactive_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr("stonepy.client.SystemClock", lambda: clock)
    logon = respx.post("https://api.example/v2/session").mock(
        side_effect=[
            httpx.Response(200, json=_logon_response("MANUAL-TOKEN")),
            httpx.Response(200, json=_logon_response("REPLAY-TOKEN")),
        ]
    )
    protected = respx.get("https://api.example/v2/clientPreference/list").mock(
        return_value=httpx.Response(200, json={"ClientPreferences": []})
    )

    async def run() -> None:
        client = AsyncStoneXClient(
            ClientConfig(base_url="https://api.example", proactive_refresh_seconds=10.0)
        )
        try:
            await client.session.log_on(_logon_request())
            clock.advance(10.0)

            response = await client.client_preference.get_client_preferences_list(["x"], 1)

            assert response.client_preferences == []
            assert len(logon.calls) == 2
            assert protected.calls[0].request.headers["Session"] == "REPLAY-TOKEN"
            assert protected.calls[0].request.headers["UserName"] == "me"
        finally:
            await client.aclose()

    asyncio.run(run())


@respx.mock
def test_async_credential_less_auth_refresh_raises_configuration_error() -> None:
    import asyncio

    from stonepy import AsyncStoneXClient, ClientConfig, ConfigurationError

    respx.get("https://api.example/v2/UserAccount/ClientAndTradingAccount").respond(401)

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            with pytest.raises(ConfigurationError, match="session refresh is not configured"):
                await client.user_account.get_client_and_trading_account()

    asyncio.run(run())
