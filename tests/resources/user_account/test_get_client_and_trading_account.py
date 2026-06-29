from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import AccountInformationResponseDTOv2

_RESPONSE_BODY = '{"AccountResult":{"LegalParties":[],"AccountHolders":[],"ClientAccounts":[],"TradingAccounts":[],"AccountOperators":[],"Contracts":[],"Restrictions":[],"LinkedClientAccounts":[],"CashEquity":{"ClientAccountToken":[]}}}'  # noqa: E501


@respx.mock
def test_get_client_and_trading_account_returns_response() -> None:
    route = respx.get("https://api.example/v2/UserAccount/ClientAndTradingAccount").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.user_account.get_client_and_trading_account()
        assert isinstance(resp, AccountInformationResponseDTOv2)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/v2/UserAccount/ClientAndTradingAccount"
    finally:
        client.close()


@respx.mock
def test_get_client_and_trading_account_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/v2/UserAccount/ClientAndTradingAccount").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            resp = await client.user_account.get_client_and_trading_account()
            assert isinstance(resp, AccountInformationResponseDTOv2)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
