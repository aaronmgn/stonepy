from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListManagedClientsResponseDTO

_RESPONSE_BODY = '{"ClientAccountId":1,"ManagedClients":[{"ClientAccountId":1,"ClientCode":"x","StartDateUtc":"/Date(1577836800000)/","EndDateUtc":"/Date(1577836800000)/","TradingAccounts":[]}]}'  # noqa: E501


@respx.mock
def test_list_managed_clients_returns_response() -> None:
    route = respx.get("https://api.example/tradingadvisor/managedclients").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        trading_account_id = 1
        resp = client.tradingadvisor.list_managed_clients(trading_account_id)
        assert isinstance(resp, ListManagedClientsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/tradingadvisor/managedclients"
        assert dict(route.calls[0].request.url.params) == {"tradingAccountId": "1"}
    finally:
        client.close()


@respx.mock
def test_list_managed_clients_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/tradingadvisor/managedclients").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            trading_account_id = 1
            resp = await client.tradingadvisor.list_managed_clients(trading_account_id)
            assert isinstance(resp, ListManagedClientsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
