from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from stonepy import OrderRejectedError, OrderStatusUnknownError
from stonepy._core.config import ClientConfig
from stonepy.client import AsyncStoneXClient, StoneXClient
from stonepy.models import ExecutionResponseDTO, ExecutionVenueRequestDTO

_RESPONSE_BODY = '{"RequestId":"x","Status":"Success","Reason":"x"}'


@respx.mock
def test_save_order_returns_response() -> None:
    route = respx.post("https://api.example/v2/order").mock(
        return_value=httpx.Response(200, content=_RESPONSE_BODY)
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example"))
    try:
        client._ctx.session.set_token("TOKEN", "user")
        request = ExecutionVenueRequestDTO.model_construct()
        resp = client.order.save_order(request)
        assert isinstance(resp, ExecutionResponseDTO)
        assert route.called
        assert route.calls[0].request.method == "POST"
        assert route.calls[0].request.url.path == "/v2/order"
    finally:
        client.close()


@respx.mock
def test_save_order_async() -> None:
    async def run() -> None:
        route = respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(200, content=_RESPONSE_BODY)
        )
        client = AsyncStoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            await client._ctx.session.aset_token("TOKEN", "user")
            request = ExecutionVenueRequestDTO.model_construct()
            resp = await client.order.save_order(request)
            assert isinstance(resp, ExecutionResponseDTO)
            assert route.called
            assert route.calls[0].request.method == "POST"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_save_order_success_status_string_returns_model() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(200, content='{"RequestId":"r1","Status":"Success"}')
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            resp = client.order.save_order(ExecutionVenueRequestDTO.model_construct())
            assert resp.status == "Success"
        finally:
            client.close()


def test_save_order_failure_status_string_raises_order_rejected() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(
                200, content='{"RequestId":"r1","Status":"Failure","Reason":"Insufficient funds"}'
            )
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            with pytest.raises(OrderRejectedError) as exc_info:
                client.order.save_order(ExecutionVenueRequestDTO.model_construct())
            assert exc_info.value.reason == "Insufficient funds"
        finally:
            client.close()


def test_save_order_unknown_text_status_raises_indeterminate_error() -> None:
    with respx.mock:
        respx.post("https://api.example/v2/order").mock(
            return_value=httpx.Response(
                200, content='{"RequestId":"r1","Status":"Queued","Reason":"Pending venue"}'
            )
        )
        client = StoneXClient(ClientConfig(base_url="https://api.example"))
        try:
            client._ctx.session.set_token("TOKEN", "user")
            with pytest.raises(OrderStatusUnknownError) as exc_info:
                client.order.save_order(ExecutionVenueRequestDTO.model_construct())
            assert exc_info.value.status == "Queued"
            assert exc_info.value.method == "POST"
            assert exc_info.value.path == "/v2/order"
        finally:
            client.close()
