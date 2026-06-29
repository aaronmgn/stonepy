from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient

# DeletePA returns a bare top-level JSON boolean on success, not an object.
_RESPONSE_BODY = "true"


@respx.mock
def test_delete_pa_returns_response() -> None:
    route = respx.post("https://api.example/pricealert/delete/1").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        alert_id = 1
        client_account_id = 1
        resp = client.price_alert.delete_pa(alert_id, client_account_id)
        assert resp is True
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/pricealert/delete/1"
    finally:
        client.close()


@respx.mock
def test_delete_pa_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/pricealert/delete/1").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            alert_id = 1
            client_account_id = 1
            resp = await client.price_alert.delete_pa(alert_id, client_account_id)
            assert resp is True
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
