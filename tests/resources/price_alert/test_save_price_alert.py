from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SaveAlertRequestDTOv2, SaveAlertResponseDTOv2

_RESPONSE_BODY = '{"AlertId":1}'


@respx.mock
def test_save_price_alert_returns_response() -> None:
    route = respx.post("https://api.example/priceAlert/v2/priceAlert/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = SaveAlertRequestDTOv2.model_construct()
        resp = client.price_alert.save_price_alert(request)
        assert isinstance(resp, SaveAlertResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/priceAlert/v2/priceAlert/save"
    finally:
        client.close()


@respx.mock
def test_save_price_alert_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/priceAlert/v2/priceAlert/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = SaveAlertRequestDTOv2.model_construct()
            resp = await client.price_alert.save_price_alert(request)
            assert isinstance(resp, SaveAlertResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
