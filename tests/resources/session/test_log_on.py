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
    return ApiLogOnRequestDTO.model_validate(
        {"UserName": "me", "Password": "pw", "AppKey": "key", "AppVersion": "v", "AppComments": ""}
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
            ApiLogOnRequestDTO.model_validate(
                {
                    "UserName": "u",
                    "Password": "p",
                    "AppKey": "k",
                    "AppVersion": "stonepy",
                    "AppComments": "",
                }
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
            ApiLogOnRequestDTO.model_validate(
                {
                    "UserName": "u",
                    "Password": "p",
                    "AppKey": "k",
                    "AppVersion": "stonepy",
                    "AppComments": "",
                }
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
                ApiLogOnRequestDTO.model_validate(
                    {
                        "UserName": "u",
                        "Password": "p",
                        "AppKey": "k",
                        "AppVersion": "stonepy",
                        "AppComments": "",
                    }
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


@respx.mock
def test_sync_manual_logon_installs_token_and_callback_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import Iterator
    from contextlib import contextmanager

    from stonepy._core.session import SessionManager

    respx.post("https://api.example/v2/session").respond(200, json={"Session": "MANUAL"})
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        manager = client._ctx.session
        assert isinstance(manager, SessionManager)
        observed: list[tuple[str | None, object]] = []
        lock = manager._lock

        @contextmanager
        def recording_lock() -> Iterator[None]:
            with lock:
                yield
                observed.append((manager._token, manager._manual_logon))

        monkeypatch.setattr(manager, "_lock", recording_lock())
        client.session.log_on(_logon_request())
        assert len(observed) == 1
        assert observed[0][0] == "MANUAL"
        assert callable(observed[0][1])


@respx.mock
def test_async_manual_logon_installs_token_and_callback_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    from stonepy._core.session import AsyncSessionManager

    respx.post("https://api.example/v2/session").respond(200, json={"Session": "MANUAL"})

    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            manager = client._ctx.session
            assert isinstance(manager, AsyncSessionManager)
            observed: list[tuple[str | None, object]] = []
            lock = manager._lock

            @asynccontextmanager
            async def recording_lock() -> AsyncIterator[None]:
                async with lock:
                    yield
                    observed.append((manager._token, manager._manual_alogon))

            monkeypatch.setattr(manager, "_lock", recording_lock())
            await client.session.log_on(_logon_request())
            assert len(observed) == 1
            assert observed[0][0] == "MANUAL"
            assert callable(observed[0][1])

    asyncio.run(run())


@respx.mock
def test_manual_logon_replay_uses_validated_request_snapshot() -> None:
    async def run() -> None:
        request = _logon_request()
        expected = request.model_dump(by_alias=True, exclude_unset=True, mode="python")
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def logon(req: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                started.set()
                await release.wait()
            return httpx.Response(200, json={"Session": f"TOKEN-{calls}"})

        route = respx.post("https://api.example/v2/session").mock(side_effect=logon)
        respx.get("https://api.example/protected").mock(
            side_effect=[httpx.Response(401), httpx.Response(200, json={"OrderId": 1})]
        )
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            task = asyncio.create_task(client.session.log_on(request))
            started_task = asyncio.create_task(started.wait())
            try:
                done, _ = await asyncio.wait_for(
                    asyncio.wait({task, started_task}, return_when=asyncio.FIRST_COMPLETED),
                    timeout=2,
                )
                if task in done:
                    await task  # Propagate an initial logon failure before waiting for the handler.
                await asyncio.wait_for(started_task, timeout=2)
                request.password = "changed-after-send"
                release.set()
                await asyncio.wait_for(task, timeout=2)
                await client._ctx.ainvoke(_PROTECTED_SPEC)
            finally:
                for pending in (task, started_task):
                    if not pending.done():
                        pending.cancel()
                await asyncio.gather(task, started_task, return_exceptions=True)
        assert calls == 2
        assert [json.loads(call.request.content) for call in route.calls] == [expected, expected]

    asyncio.run(run())


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_failed_manual_logon_preserves_previous_callback(asynchronous: bool) -> None:
    from stonepy._core.session import AsyncSessionManager, SessionManager

    respx.post("https://api.example/v2/session").mock(
        side_effect=[
            httpx.Response(200, json={"Session": "FIRST"}),
            httpx.Response(200, json={"Session": None}),
            httpx.Response(200, json={"Session": "REPLAY"}),
        ]
    )
    respx.get("https://api.example/protected").mock(
        side_effect=[httpx.Response(401), httpx.Response(200, json={"OrderId": 1})]
    )

    async def run() -> None:
        if asynchronous:
            async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
                manager = client._ctx.session
                assert isinstance(manager, AsyncSessionManager)
                await client.session.log_on(_logon_request())
                original: object = manager._manual_alogon
                with pytest.raises(AuthenticationError):
                    await client.session.log_on(_logon_request())
                assert manager._manual_alogon is original
                assert manager._token == "FIRST"
                await client._ctx.ainvoke(_PROTECTED_SPEC)
                assert manager._token == "REPLAY"
        else:
            with StoneXClient(ClientConfig(base_url="https://api.example")) as sync_client:
                sync_manager = sync_client._ctx.session
                assert isinstance(sync_manager, SessionManager)
                sync_client.session.log_on(_logon_request())
                original = sync_manager._manual_logon
                with pytest.raises(AuthenticationError):
                    sync_client.session.log_on(_logon_request())
                assert sync_manager._manual_logon is original
                assert sync_manager._token == "FIRST"
                sync_client._ctx.invoke(_PROTECTED_SPEC)
                assert sync_manager._token == "REPLAY"

    asyncio.run(run())
