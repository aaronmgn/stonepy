import asyncio
import json

import httpx
import pytest
import respx
from pydantic import Field

from stonepy import AuthenticationError, StoneXClient
from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.models import ResponseModel
from stonepy.client import AsyncStoneXClient
from stonepy.models import ApiLogOnRequestDTO


def _logon_request() -> ApiLogOnRequestDTO:
    return ApiLogOnRequestDTO(
        UserName="me", Password="pw", AppKey="key", AppVersion="v", AppComments=""
    )


class _ProtectedResp(ResponseModel):
    order_id: int = Field(alias="OrderId")


_PROTECTED_SPEC = EndpointSpec(
    name="Protected",
    method="GET",
    path="/protected",
    idempotent=True,
    auth_policy=AuthPolicy.SESSION,
    rate_limit_bucket="session",
    response_model=_ProtectedResp,
)


@respx.mock
def test_log_on_returns_session() -> None:
    route = respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(
            200,
            json={
                "Session": "TOKEN-123",
                "PasswordChangeRequired": False,
                "AllowedAccountOperator": False,
                "StatusCode": 1,
                "Is2FAEnabled": False,
                "TwoFAToken": "",
                "Additional2FAMethods": [],
            },
        )
    )

    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("STALE", "old-user")
        resp = client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="u",
                Password="p",
                AppKey="k",
                AppVersion="stonepy",
                AppComments="",
            )
        )

        assert resp.session == "TOKEN-123"
        assert json.loads(route.calls[0].request.content) == {
            "UserName": "u",
            "Password": "p",
            "AppKey": "k",
            "AppVersion": "stonepy",
            "AppComments": "",
        }
        assert "session" not in route.calls[0].request.headers
        assert "username" not in route.calls[0].request.headers
        assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {
            "Session": "TOKEN-123",
            "UserName": "u",
        }
    finally:
        client.close()


@respx.mock
def test_log_on_installs_refresh_callback_for_later_401() -> None:
    respx.post("https://api.example/v2/session").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "Session": "TOKEN-123",
                    "PasswordChangeRequired": False,
                    "AllowedAccountOperator": False,
                    "StatusCode": 1,
                    "Is2FAEnabled": False,
                    "TwoFAToken": "",
                    "Additional2FAMethods": [],
                },
            ),
            httpx.Response(
                200,
                json={
                    "Session": "TOKEN-456",
                    "PasswordChangeRequired": False,
                    "AllowedAccountOperator": False,
                    "StatusCode": 1,
                    "Is2FAEnabled": False,
                    "TwoFAToken": "",
                    "Additional2FAMethods": [],
                },
            ),
        ]
    )
    protected = respx.get("https://api.example/protected").mock(
        side_effect=[
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "expired", "HttpStatus": 401},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )

    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client.session.log_on(
            ApiLogOnRequestDTO(
                UserName="u",
                Password="p",
                AppKey="k",
                AppVersion="stonepy",
                AppComments="",
            )
        )

        resp = client._ctx.invoke(_PROTECTED_SPEC)

        assert resp.order_id == 7
        assert protected.calls[0].request.headers["Session"] == "TOKEN-123"
        assert protected.calls[1].request.headers["Session"] == "TOKEN-456"
    finally:
        client.close()


@respx.mock
def test_config_credentials_refresh_replays_with_username() -> None:
    logon = respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(
            200,
            json={
                "Session": "TOKEN-123",
                "PasswordChangeRequired": False,
                "AllowedAccountOperator": False,
                "StatusCode": 1,
                "Is2FAEnabled": False,
                "TwoFAToken": "",
                "Additional2FAMethods": [],
            },
        )
    )
    protected = respx.get("https://api.example/protected").mock(
        side_effect=[
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "expired", "HttpStatus": 401},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )

    client = StoneXClient(
        ClientConfig(
            base_url="https://api.example",
            username="u",
            password="p",
            app_key="k",
        )
    )
    try:
        resp = client._ctx.invoke(_PROTECTED_SPEC)

        assert resp.order_id == 7
        assert json.loads(logon.calls[0].request.content) == {
            "UserName": "u",
            "Password": "p",
            "AppKey": "k",
            "AppVersion": "stonepy",
            "AppComments": "",
        }
        assert protected.calls[1].request.headers["Session"] == "TOKEN-123"
        assert protected.calls[1].request.headers["UserName"] == "u"
    finally:
        client.close()


@respx.mock
def test_async_log_on_returns_and_stores_session() -> None:
    respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(
            200,
            json={
                "Session": "ASYNC-TOKEN-123",
                "PasswordChangeRequired": False,
                "AllowedAccountOperator": False,
                "StatusCode": 1,
                "Is2FAEnabled": False,
                "TwoFAToken": "",
                "Additional2FAMethods": [],
            },
        )
    )

    async def run() -> None:
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            resp = await client.session.log_on(
                ApiLogOnRequestDTO(
                    UserName="u",
                    Password="p",
                    AppKey="k",
                    AppVersion="stonepy",
                    AppComments="",
                )
            )

            assert resp.session == "ASYNC-TOKEN-123"
            assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {
                "Session": "ASYNC-TOKEN-123",
                "UserName": "u",
            }
        finally:
            await client.aclose()

    asyncio.run(run())


@respx.mock
def test_async_config_credentials_refresh_replays_with_username() -> None:
    respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(
            200,
            json={
                "Session": "ASYNC-TOKEN-123",
                "PasswordChangeRequired": False,
                "AllowedAccountOperator": False,
                "StatusCode": 1,
                "Is2FAEnabled": False,
                "TwoFAToken": "",
                "Additional2FAMethods": [],
            },
        )
    )
    protected = respx.get("https://api.example/protected").mock(
        side_effect=[
            httpx.Response(
                401,
                json={"ErrorCode": 4011, "ErrorMessage": "expired", "HttpStatus": 401},
            ),
            httpx.Response(200, json={"OrderId": 7}),
        ]
    )

    async def run() -> None:
        client = AsyncStoneXClient(
            ClientConfig(
                base_url="https://api.example",
                username="u",
                password="p",
                app_key="k",
            )
        )
        try:
            resp = await client._ctx.ainvoke(_PROTECTED_SPEC)

            assert resp.order_id == 7
            assert protected.calls[1].request.headers["Session"] == "ASYNC-TOKEN-123"
            assert protected.calls[1].request.headers["UserName"] == "u"
        finally:
            await client.aclose()

    asyncio.run(run())


@respx.mock
def test_log_on_without_session_token_raises_and_preserves_refresh_callable() -> None:
    respx.post("https://api.example/v2/session").mock(
        return_value=httpx.Response(200, content='{"StatusCode":1}')
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        original_logon = client._ctx.logon
        with pytest.raises(AuthenticationError):
            client.session.log_on(_logon_request())
        assert client._ctx.logon is original_logon
    finally:
        client.close()
