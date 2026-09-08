from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import PriceAlertResponseDTO

_RESPONSE_BODY = '{"PriceAlerts":[{"AlertId":1,"MarketId":1,"Criterion":1,"Direction":1,"FillRate":"1.23","EmailAddress":"x","Expiry":1,"ExpiryDate":"/Date(1577836800000)/","CreateDate":"/Date(1577836800000)/","Comment":"x","NotificationMethod":1}]}'  # noqa: E501


@respx.mock
@pytest.mark.parametrize("alert_id", [None, 1])
def test_get_pa_returns_response(alert_id: int | None) -> None:
    route = respx.get("https://api.example/pricealert/").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 123
        resp = client.price_alert.get_pa(client_account_id, alert_id=alert_id)
        assert isinstance(resp, PriceAlertResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/pricealert/"
        expected_query = {"ClientAccountId": "123"}
        if alert_id is not None:
            expected_query["alertId"] = str(alert_id)
        assert dict(route.calls[0].request.url.params) == expected_query
        assert route.calls[0].request.content == b""
    finally:
        client.close()


@respx.mock
@pytest.mark.parametrize("alert_id", [None, 1])
def test_get_pa_async(alert_id: int | None) -> None:
    async def run() -> None:
        route = respx.get("https://api.example/pricealert/").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 123
            resp = await client.price_alert.get_pa(client_account_id, alert_id=alert_id)
            assert isinstance(resp, PriceAlertResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
            expected_query = {"ClientAccountId": "123"}
            if alert_id is not None:
                expected_query["alertId"] = str(alert_id)
            assert dict(route.calls[0].request.url.params) == expected_query
            assert route.calls[0].request.content == b""
        finally:
            await client.aclose()

    asyncio.run(run())
