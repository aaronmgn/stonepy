from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import ResponseModel
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SaveAlertRequestDTOv2


@respx.mock
def test_save_pa_returns_response() -> None:
    route = respx.post("https://api.example/pricealert/").mock(
        return_value=httpx.Response(200, json={})
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = SaveAlertRequestDTOv2.model_construct()
        resp = client.price_alert.save_pa(request)
        assert isinstance(resp, ResponseModel)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/pricealert/"
    finally:
        client.close()


@respx.mock
def test_save_pa_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/pricealert/").mock(
            return_value=httpx.Response(200, json={})
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = SaveAlertRequestDTOv2.model_construct()
            resp = await client.price_alert.save_pa(request)
            assert isinstance(resp, ResponseModel)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
