from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ClientAccountMarginResponseDTO

_RESPONSE_BODY = '{"Cash":"1.23","Margin":"1.23","MarginIndicator":"1.23","NetEquity":"1.23","OpenTradeEquity":"1.23","TradableFunds":"1.23","PendingFunds":"1.23","TradingResource":"1.23","TotalMarginRequirement":"1.23","CurrencyId":1,"CurrencyIsoCode":"x"}'  # noqa: E501


@respx.mock
def test_get_client_account_margin_returns_response() -> None:
    route = respx.get("https://api.example/margin/v2/margin/clientAccountMargin").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        client_account_id = 1
        resp = client.margin.get_client_account_margin(client_account_id)
        assert isinstance(resp, ClientAccountMarginResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/margin/v2/margin/clientAccountMargin"
    finally:
        client.close()


@respx.mock
def test_get_client_account_margin_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/margin/v2/margin/clientAccountMargin").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            client_account_id = 1
            resp = await client.margin.get_client_account_margin(client_account_id)
            assert isinstance(resp, ClientAccountMarginResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
