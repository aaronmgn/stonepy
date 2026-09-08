from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy._core.models import UnspecifiedResponse
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
        assert isinstance(resp, UnspecifiedResponse)
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
            assert isinstance(resp, UnspecifiedResponse)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


def _valid_alert_request() -> SaveAlertRequestDTOv2:
    return SaveAlertRequestDTOv2.model_validate(
        {
            "ClientAccountId": 1,
            "AlertId": 0,
            "MarketId": 2,
            "Criterion": 1,
            "Direction": 1,
            "FillRate": "1.2345",
            "EmailAddress": "",
            "Expiry": 1,
            "ExpiryDate": None,
            "Comment": "unit test",
            "NotificationMethod": 1,
        }
    )


@pytest.mark.parametrize("body", [b"", b"null"])
@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_save_pa_returns_unspecified_response_for_empty_body(
    body: bytes, asynchronous: bool
) -> None:
    response = _call_save_pa(body, asynchronous)
    assert isinstance(response, UnspecifiedResponse)
    assert response.model_extra == {}


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_save_pa_retains_unexpected_object_fields(asynchronous: bool) -> None:
    response = _call_save_pa(b'{"a":1}', asynchronous)
    assert response.model_extra == {"a": 1}


def _call_save_pa(body: bytes, asynchronous: bool) -> UnspecifiedResponse:
    respx.request("POST", "https://api.example/pricealert/").respond(200, content=body)

    async def run() -> UnspecifiedResponse:
        async with AsyncStoneXClient(ClientConfig(base_url="https://api.example")) as client:
            await client._ctx.session.aset_token("TOKEN", "user")
            return await client.price_alert.save_pa(_valid_alert_request())

    if asynchronous:
        return asyncio.run(run())
    with StoneXClient(ClientConfig(base_url="https://api.example")) as client:
        client._ctx.session.set_token("TOKEN", "user")
        return client.price_alert.save_pa(_valid_alert_request())
