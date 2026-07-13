from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import AuthPolicy
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiLogOffResponseDTO

_RESPONSE_BODY = '{"LoggedOut":false}'


@respx.mock
def test_delete_session_returns_response() -> None:
    route = respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        user_name = "x"
        session = "x"
        resp = client.session.delete_session(user_name, session)
        assert isinstance(resp, ApiLogOffResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/session/deleteSession"
    finally:
        client.close()


@respx.mock
def test_delete_session_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/session/deleteSession").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            user_name = "x"
            session = "x"
            resp = await client.session.delete_session(user_name, session)
            assert isinstance(resp, ApiLogOffResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


@respx.mock
def test_delete_session_async_clears_local_token_on_success() -> None:
    async def run() -> None:
        respx.post("https://api.example/session/deleteSession").mock(
            return_value=httpx.Response(200, content='{"LoggedOut":true}')
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            await client.session.delete_session("user", "TOKEN")
            assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {}
        finally:
            await client.aclose()

    asyncio.run(run())


@respx.mock
def test_delete_session_clears_local_token_on_success() -> None:
    respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content='{"LoggedOut":true}')
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client.session.delete_session("user", "TOKEN")
        assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {}
    finally:
        client.close()


@respx.mock
def test_delete_session_keeps_token_when_deleting_a_different_session() -> None:
    respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content='{"LoggedOut":true}')
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("CURRENT", "user")
        client.session.delete_session("user", "OTHER")
        assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {
            "Session": "CURRENT",
            "UserName": "user",
        }
    finally:
        client.close()


@respx.mock
def test_delete_session_missing_logged_out_clears_matching_token() -> None:
    # ASSUMPTION not backed by docs: ApiLogOffResponseDTO documents only "true == successful
    # log out" and is silent on whether LoggedOut can be omitted on HTTP 200. We currently
    # treat an absent flag as success (clear the matching token); the nightly live logoff
    # probe exists to catch the real API contradicting this.
    respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content="{}")
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client.session.delete_session("user", "TOKEN")
        assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {}
    finally:
        client.close()


@respx.mock
def test_delete_session_keeps_token_when_logoff_reports_false() -> None:
    respx.post("https://api.example/session/deleteSession").mock(
        return_value=httpx.Response(200, content='{"LoggedOut":false}')
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client.session.delete_session("user", "TOKEN")
        assert client._ctx.session.auth_headers(AuthPolicy.SESSION) == {
            "Session": "TOKEN",
            "UserName": "user",
        }
    finally:
        client.close()
