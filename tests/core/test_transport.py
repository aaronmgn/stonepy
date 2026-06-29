import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
import respx
from pydantic import Field

from stonepy._core.clock import FakeClock
from stonepy._core.config import ClientConfig
from stonepy._core.endpoint import AuthPolicy, EndpointSpec, Param
from stonepy._core.models import RequestModel, ResponseModel
from stonepy._core.transport import Request, SyncTransport, build_request
from stonepy.client import StoneXClient
from stonepy.models import GetPriceTickResponseDTO


class _Body(RequestModel):
    quantity: Decimal = Field(alias="Quantity")


class _Resp(ResponseModel):
    pass


_PRICE_TICK_RESPONSE = '{"PriceTicks":[{"TickDate":"/Date(1577836800000)/","Price":"1.23"}]}'


def _order_spec() -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name="Order",
        method="POST",
        path="/order/{OrderId}",
        idempotent=False,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        request_model=_Body,
        response_model=_Resp,
        params=(Param("OrderId", "path", "order_id"), Param("body", "body", "body")),
    )


def _catalog_spec(path: str) -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name="Catalog",
        method="GET",
        path=path,
        idempotent=True,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        response_model=_Resp,
        params=(),
    )


def _host_rooted_spec() -> EndpointSpec[_Resp]:
    return EndpointSpec(
        name="LogOn v2",
        method="POST",
        path="/v2/session",
        idempotent=False,
        auth_policy=AuthPolicy.NONE,
        rate_limit_bucket="session",
        response_model=_Resp,
        host_rooted=True,
        params=(),
    )


def test_build_request_host_rooted_drops_base_path() -> None:
    req = build_request(
        "https://ciapi.cityindex.com/TradingAPI",
        _host_rooted_spec(),
        path_params={},
        query={},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://ciapi.cityindex.com/v2/session"


def test_build_request_host_rooted_preserves_scheme_host_and_port() -> None:
    req = build_request(
        "https://ciapipreprod.cityindextest9.co.uk:8443/TradingApi/",
        _host_rooted_spec(),
        path_params={},
        query={},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://ciapipreprod.cityindextest9.co.uk:8443/v2/session"


def test_build_request_base_rooted_keeps_base_path() -> None:
    req = build_request(
        "https://ciapi.cityindex.com/TradingAPI",
        _catalog_spec("/margin/ClientAccountMargin"),
        path_params={},
        query={},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://ciapi.cityindex.com/TradingAPI/margin/ClientAccountMargin"


def test_build_request_path_and_json_body_with_decimal_number() -> None:
    spec = _order_spec()
    req = build_request(
        "https://api.example",
        spec,
        path_params={"OrderId": 5},
        query={},
        body_dict={"Quantity": Decimal("1.30")},
        auth_headers={"Session": "T", "UserName": "u"},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/order/5"
    assert b'"Quantity":1.30' in (req.content or b"")
    assert req.headers["Session"] == "T"
    assert req.headers["Content-Type"] == "application/json"
    assert req.headers["User-Agent"] == "stonepy/0.1"


def test_build_request_percent_encodes_path_params() -> None:
    req = build_request(
        "https://api.example",
        _order_spec(),
        path_params={"OrderId": "a/b?c#d"},
        query={},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/order/a%2Fb%3Fc%23d"


def test_build_request_missing_path_param_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Missing path params"):
        build_request(
            "https://api.example",
            _order_spec(),
            path_params={},
            query={},
            body_dict=None,
            auth_headers={},
            user_agent="stonepy/0.1",
        )


def test_build_request_extra_path_param_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unexpected path params"):
        build_request(
            "https://api.example",
            _order_spec(),
            path_params={"OrderId": 5, "Other": 6},
            query={},
            body_dict=None,
            auth_headers={},
            user_agent="stonepy/0.1",
        )


def test_build_request_none_path_param_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Path params cannot be None"):
        build_request(
            "https://api.example",
            _order_spec(),
            path_params={"OrderId": None},
            query={},
            body_dict=None,
            auth_headers={},
            user_agent="stonepy/0.1",
        )


def test_build_request_stringifies_non_none_query_params() -> None:
    req = build_request(
        "https://api.example",
        _order_spec(),
        path_params={"OrderId": 5},
        query={"A": 1, "B": None, "C": True},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.params == {"A": "1", "C": "true"}


def test_build_request_serializes_bool_values_in_query_templates() -> None:
    req = build_request(
        "https://api.example",
        _catalog_spec("/spread/markets?includeOptions={includeOptions}"),
        path_params={},
        query={"IncludeOptions": False},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )

    assert req.params == {"includeOptions": "false"}


def test_build_request_serializes_datetime_query_values_as_wcf_dates() -> None:
    req = build_request(
        "https://api.example",
        _order_spec(),
        path_params={"OrderId": 5},
        query={"From": datetime(2026, 6, 17, 12, 30, tzinfo=UTC)},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )

    assert req.params == {"From": "/Date(1781699400000)/"}


def test_build_request_catalog_query_template_uses_template_key_without_duplicate() -> None:
    req = build_request(
        "https://api.example",
        _catalog_spec("/margin/v2/margin/clientAccountMargin?clientAccountId={clientAccountId}"),
        path_params={},
        query={"ClientAccountId": 123},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/margin/v2/margin/clientAccountMargin"
    assert "{" not in req.url and "}" not in req.url
    assert "?" not in req.url
    assert req.params == {"clientAccountId": "123"}


def test_build_request_catalog_query_template_serializes_array_value() -> None:
    req = build_request(
        "https://api.example",
        _catalog_spec("/watchlist/v2/watchlists/list?clientAccountId={clientAccountId}&ids={ids}"),
        path_params={},
        query={"ClientAccountId": 1, "Ids": [10, 20]},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/watchlist/v2/watchlists/list"
    assert req.params == {"clientAccountId": "1", "ids": "10,20"}


def test_build_request_catalog_path_and_query_templates_match_query_case_insensitively() -> None:
    req = build_request(
        "https://api.example",
        _catalog_spec("/market/v2/market/{marketId}/information?clientAccountId={clientAccountId}"),
        path_params={},
        query={"MarketId": "M1", "ClientAccountId": 7},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/market/v2/market/M1/information"
    assert "{" not in req.url and "}" not in req.url
    assert req.params == {"clientAccountId": "7"}


def test_build_request_missing_query_template_value_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Missing template value"):
        build_request(
            "https://api.example",
            _catalog_spec("/market/v2/market/spread?clientAccountId={clientAccountId}"),
            path_params={},
            query={},
            body_dict=None,
            auth_headers={},
            user_agent="stonepy/0.1",
        )


def test_build_request_none_query_template_value_omits_segment() -> None:
    req = build_request(
        "https://api.example",
        _catalog_spec("/order/openpositions?TradingAccountId={TradingAccountId}"),
        path_params={},
        query={"TradingAccountId": None},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.url == "https://api.example/order/openpositions"
    assert req.params == {}
    assert "TradingAccountId" not in req.url


def test_build_request_ordinary_query_serializes_array_value() -> None:
    req = build_request(
        "https://api.example",
        _order_spec(),
        path_params={"OrderId": 5},
        query={"Ids": [10, 20]},
        body_dict=None,
        auth_headers={},
        user_agent="stonepy/0.1",
    )
    assert req.params == {"Ids": "10,20"}


def test_build_request_query_sequence_with_none_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Query sequence values cannot contain None"):
        build_request(
            "https://api.example",
            _order_spec(),
            path_params={"OrderId": 5},
            query={"Ids": [10, None]},
            body_dict=None,
            auth_headers={},
            user_agent="stonepy/0.1",
        )


@respx.mock
def test_public_client_replays_429_then_success_with_respx_transport() -> None:
    route = respx.get("https://api.example/market/x/tickhistory").mock(
        side_effect=[
            httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ErrorCode": 5002, "ErrorMessage": "busy", "HttpStatus": 429},
            ),
            httpx.Response(200, content=_PRICE_TICK_RESPONSE),
        ]
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example", max_retries=1))
    client._ctx.clock = FakeClock()
    try:
        client._ctx.session.set_token("TOKEN", "user")

        resp = client.market.get_latest_price_ticks("x", 1, "bid")

        assert isinstance(resp, GetPriceTickResponseDTO)
        assert route.called
        assert len(route.calls) == 2
        assert route.calls[0].request.headers["Session"] == "TOKEN"
        assert route.calls[1].request.url.path == "/market/x/tickhistory"
    finally:
        client.close()


@respx.mock
def test_public_client_replays_connect_error_then_success_with_respx_transport() -> None:
    route = respx.get("https://api.example/market/x/tickhistory").mock(
        side_effect=[
            httpx.ConnectError("temporary"),
            httpx.Response(200, content=_PRICE_TICK_RESPONSE),
        ]
    )
    client = StoneXClient(ClientConfig(base_url="https://api.example", max_retries=1))
    clock = FakeClock()
    client._ctx.clock = clock
    client._ctx.jitter = lambda: 1.0
    try:
        client._ctx.session.set_token("TOKEN", "user")

        resp = client.market.get_latest_price_ticks("x", 1, "bid")

        assert isinstance(resp, GetPriceTickResponseDTO)
        assert route.called
        assert len(route.calls) == 2
        assert clock.now() == 1.0
    finally:
        client.close()


def test_request_repr_redacts_session_header() -> None:
    text = repr(Request("GET", "https://api.example/ping", {"Session": "SECRET"}, {}, None))
    assert "SECRET" not in text
    assert "***" in text


def test_request_repr_redacts_secret_query_params() -> None:
    text = repr(
        Request(
            "GET",
            "https://api.example/search",
            {},
            {
                "A": "visible",
                "Session": "SESSION-SECRET",
                "Password": "PW-SECRET",
                "AppKey": "APP-SECRET",
            },
            None,
        )
    )
    assert "visible" in text
    assert "SESSION-SECRET" not in text
    assert "PW-SECRET" not in text
    assert "APP-SECRET" not in text
    assert "***" in text


def test_request_repr_redacts_secret_url_query_params() -> None:
    text = repr(
        Request(
            "GET",
            "https://api.example/search?A=visible&Password=PW-SECRET&Session=S-SECRET&AppKey=K-SECRET",
            {},
            {},
            None,
        )
    )
    assert "visible" in text
    assert "PW-SECRET" not in text
    assert "S-SECRET" not in text
    assert "K-SECRET" not in text
    assert "***" in text


def test_request_repr_redacts_content_body() -> None:
    text = repr(
        Request(
            "POST",
            "https://api.example/session",
            {},
            {},
            b'{"Password":"PW-SECRET","AppKey":"APP-SECRET"}',
        )
    )
    assert "PW-SECRET" not in text
    assert "APP-SECRET" not in text
    assert "<redacted" in text


@respx.mock
def test_sync_transport_send() -> None:
    route = respx.get("https://api.example/ping?A=1").mock(
        return_value=httpx.Response(200, json={"ok": 1})
    )
    t = SyncTransport(base_url="https://api.example", verify=True, timeout=5.0)

    resp = t.send(Request("GET", "https://api.example/ping", {}, {"A": "1"}, None))
    assert resp.status_code == 200
    assert route.called
    assert str(resp.request.url) == "https://api.example/ping?A=1"
    t.close()


@respx.mock
def test_sync_transport_constructed_from_client_config_sends() -> None:
    route = respx.get("https://api.example/ping?A=1").mock(
        return_value=httpx.Response(200, json={"ok": 1})
    )
    t = SyncTransport(
        ClientConfig(
            base_url="https://api.example",
            connect_timeout=1.0,
            read_timeout=2.0,
            write_timeout=3.0,
            pool_timeout=4.0,
            max_connections=7,
            verify_tls=True,
            proxy=None,
        )
    )

    resp = t.send(Request("GET", "/ping", {}, {"A": "1"}, None))
    assert resp.status_code == 200
    assert route.called
    assert str(resp.request.url) == "https://api.example/ping?A=1"
    t.close()


@respx.mock
def test_async_transport_asend() -> None:
    from stonepy._core.transport import AsyncTransport

    route = respx.get("https://api.example/ping?A=1").mock(
        return_value=httpx.Response(200, json={"ok": 1})
    )

    async def run() -> None:
        t = AsyncTransport(base_url="https://api.example", verify=True, timeout=5.0)
        resp = await t.asend(Request("GET", "https://api.example/ping", {}, {"A": "1"}, None))
        assert resp.status_code == 200
        assert route.called
        assert str(resp.request.url) == "https://api.example/ping?A=1"
        await t.aclose()

    asyncio.run(run())
