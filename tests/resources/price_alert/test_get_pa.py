from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import PriceAlertResponseDTO

_RESPONSE_BODY = '{"PriceAlerts":[{"AlertId":1,"MarketId":1,"Criterion":1,"Direction":1,"FillRate":"1.23","EmailAddress":"x","Expiry":1,"ExpiryDate":"/Date(1577836800000)/","CreateDate":"/Date(1577836800000)/","Comment":"x","NotificationMethod":1}]}'  # noqa: E501


@respx.mock
def test_get_pa_returns_response() -> None:
    route = respx.get("https://api.example/pricealert/").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        alert_id = 1
        client_account_id = 1
        resp = client.price_alert.get_pa(client_account_id, alert_id=alert_id)
        assert isinstance(resp, PriceAlertResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pricealert/"
    finally:
        client.close()


@respx.mock
def test_get_pa_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pricealert/").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            alert_id = 1
            client_account_id = 1
            resp = await client.price_alert.get_pa(client_account_id, alert_id=alert_id)
            assert isinstance(resp, PriceAlertResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
