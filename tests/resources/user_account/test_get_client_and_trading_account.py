from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import AccountResult

# The live endpoint returns the AccountResult fields flat at the top level (and in camelCase), not
# wrapped under an "AccountResult" key. Keys are intentionally camelCase to exercise the response
# model's case-insensitive matching end to end.
_RESPONSE_BODY = (
    '{"legalParties":[{"partyId":1}],"clientAccounts":[{"clientAccountId":111}],'
    '"tradingAccounts":[{"tradingAccountId":222}],"accountOperators":[{"accountOperatorId":3}]}'
)


@respx.mock
def test_get_client_and_trading_account_returns_response() -> None:
    route = respx.get("https://api.example/v2/UserAccount/ClientAndTradingAccount").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        resp = client.user_account.get_client_and_trading_account()
        assert isinstance(resp, AccountResult)
        assert resp.client_accounts is not None
        assert resp.client_accounts[0].client_account_id == 111
        assert resp.trading_accounts is not None
        assert resp.trading_accounts[0].trading_account_id == 222
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
            assert isinstance(resp, AccountResult)
            assert resp.client_accounts is not None
            assert resp.client_accounts[0].client_account_id == 111
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
