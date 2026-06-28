from __future__ import annotations

import asyncio

import httpx
import respx

from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import SaveAllocationProfileRequestDTO, SaveAllocationProfileResponseDTO

_RESPONSE_BODY = "{}"


@respx.mock
def test_save_allocation_profile_returns_response() -> None:
    route = respx.post("https://api.example/tradingadvisor/allocationprofile/save").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = SaveAllocationProfileRequestDTO.model_construct()
        resp = client.tradingadvisor.save_allocation_profile(request)
        assert isinstance(resp, SaveAllocationProfileResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/tradingadvisor/allocationprofile/save"
    finally:
        client.close()


@respx.mock
def test_save_allocation_profile_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/tradingadvisor/allocationprofile/save").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = SaveAllocationProfileRequestDTO.model_construct()
            resp = await client.tradingadvisor.save_allocation_profile(request)
            assert isinstance(resp, SaveAllocationProfileResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())
