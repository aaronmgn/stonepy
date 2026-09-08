from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy.models import SingleActiveStopLimitOrderResponseDTO


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@respx.mock
def test_order_including_closed_alias_delegates(async_client: bool) -> None:
    route = respx.get("https://api.example/v2/orderIncludingClosed/42").mock(
        return_value=httpx.Response(200, json={"ActiveStopLimitOrder": {"OrderId": 42}})
    )
    config = ClientConfig(base_url="https://api.example")

    async def run() -> SingleActiveStopLimitOrderResponseDTO:
        async with AsyncStoneXClient(config) as client:
            await client._ctx.session.aset_token("TOKEN", "user")
            return await client.order.get_order_including_closed(42, 17)

    if async_client:
        response = asyncio.run(run())
    else:
        with StoneXClient(config) as client:
            client._ctx.session.set_token("TOKEN", "user")
            response = client.order.get_order_including_closed(42, 17)

    assert isinstance(response, SingleActiveStopLimitOrderResponseDTO)
    assert response.active_stop_limit_order is not None
    assert response.active_stop_limit_order.order_id == 42
    assert route.call_count == 1
    request = route.calls[0].request
    assert request.method == "GET"
    assert dict(request.url.params) == {"clientAccountId": "17"}
    assert request.content == b""
    assert request.headers["Session"] == "TOKEN"
