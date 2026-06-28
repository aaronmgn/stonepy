from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListAllocationProfilesResponseDTO

_RESPONSE_BODY = '{"AllocationProfiles":[{"Id":1,"TradingAccountId":1,"TradingAccountCode":"x","Name":"x","TypeId":1,"IsDefault":false,"Entries":[]}]}'  # noqa: E501


@respx.mock
def test_list_allocation_profiles_returns_response() -> None:
    route = respx.get("https://api.example/tradingadvisor/allocationprofiles").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        trading_account_id = 1
        resp = client.tradingadvisor.list_allocation_profiles(trading_account_id)
        assert isinstance(resp, ListAllocationProfilesResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/tradingadvisor/allocationprofiles"
        assert dict(route.calls[0].request.url.params) == {"tradingAccountId": "1"}
    finally:
        client.close()


@respx.mock
def test_list_allocation_profiles_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/tradingadvisor/allocationprofiles").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            trading_account_id = 1
            resp = await client.tradingadvisor.list_allocation_profiles(trading_account_id)
            assert isinstance(resp, ListAllocationProfilesResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
