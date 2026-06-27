from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ListCfdMarketsResponseDTO

_RESPONSE_BODY = '{"Markets":[{"MarketId":1,"Name":"x","Weighting":1}]}'


@respx.mock
def test_list_cfd_markets_returns_response() -> None:
    route = respx.get("https://api.example/cfd/markets").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        market_name = "x"
        market_code = "x"
        client_account_id = 1
        trading_account_id = 1
        max_results = 1
        use_mobile_short_name = False
        include_options = False
        resp = client.cfd.list_cfd_markets(
            client_account_id,
            market_name=market_name,
            market_code=market_code,
            max_results=max_results,
            use_mobile_short_name=use_mobile_short_name,
            include_options=include_options,
            trading_account_id=trading_account_id,
        )
        assert isinstance(resp, ListCfdMarketsResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "GET"
        assert route.calls[0].request.url.path == "/cfd/markets"
    finally:
        client.close()


@respx.mock
def test_list_cfd_markets_async() -> None:
    async def run() -> None:
        route = respx.get("https://api.example/cfd/markets").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            market_name = "x"
            market_code = "x"
            client_account_id = 1
            trading_account_id = 1
            max_results = 1
            use_mobile_short_name = False
            include_options = False
            resp = await client.cfd.list_cfd_markets(
                client_account_id,
                market_name=market_name,
                market_code=market_code,
                max_results=max_results,
                use_mobile_short_name=use_mobile_short_name,
                include_options=include_options,
                trading_account_id=trading_account_id,
            )
            assert isinstance(resp, ListCfdMarketsResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "GET"
        finally:
            await client.aclose()

    asyncio.run(run())
