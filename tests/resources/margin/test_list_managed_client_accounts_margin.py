from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ApiManagedClientAccountsMarginResponseDTO

_RESPONSE_BODY = '{"ClientAccountsMargin":[{}]}'


@respx.mock
def test_list_managed_client_accounts_margin_returns_response() -> None:
    route = respx.get("https://api.example/margin/ManagedClientAccountsMargin").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.margin.list_managed_client_accounts_margin()
        assert isinstance(resp, ApiManagedClientAccountsMarginResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/margin/ManagedClientAccountsMargin"
    finally:
        client.close()


@respx.mock
def test_list_managed_client_accounts_margin_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/margin/ManagedClientAccountsMargin").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.margin.list_managed_client_accounts_margin()
            assert isinstance(resp, ApiManagedClientAccountsMarginResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
