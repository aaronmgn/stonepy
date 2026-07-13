from __future__ import annotations

from importlib import import_module
from typing import Any

from stonepy import _endpoints
from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.status import StatusDomain
from stonepy._endpoints.client_preference import GET_CLIENT_PREFERENCES_LIST_SPEC
from stonepy._endpoints.market import GET_MARKET_INFORMATION_SPEC
from stonepy._endpoints.order import (
    GET_ACTIVE_STOP_LIMIT_ORDER_SPEC,
    GET_OPEN_POSITION_SPEC,
    LIST_ACTIVE_ORDERS_SPEC,
    SAVE_ORDER_SPEC,
)
from stonepy._endpoints.session import LOG_ON_SPEC
from stonepy.models import (
    ApiLogOnRequestDTO,
    ApiLogOnResponseDTOv2,
    GetMarketInformationResponseDTOv2,
    ListActiveOrdersRequestDTO,
    ListActiveOrdersResponseDTO,
)

_STATUS_DOMAINS = {
    ("fixedmargin", "TradeFM"): StatusDomain.INSTRUCTION,
    ("fixedmargin", "UpdateTradeFM"): StatusDomain.INSTRUCTION,
    ("order", "CancelOrder"): StatusDomain.INSTRUCTION,
    ("order", "GetActiveStopLimitOrder v2"): StatusDomain.NONE,
    ("order", "GetOpenPosition v2"): StatusDomain.NONE,
    ("order", "GetOrderHistory v2"): StatusDomain.NONE,
    ("order", "GetOrders v2"): StatusDomain.NONE,
    ("order", "ListActiveStopLimitOrders"): StatusDomain.NONE,
    ("order", "ListOpenPositions"): StatusDomain.NONE,
    ("order", "ListStopLimitOrderHistory"): StatusDomain.NONE,
    ("order", "Order"): StatusDomain.INSTRUCTION,
    ("order", "SaveOrder v2"): StatusDomain.EXECUTION_TEXT,
    ("order", "SimulateCancelOrder"): StatusDomain.ORDER,
    ("order", "SimulateOrder"): StatusDomain.ORDER,
    ("order", "SimulateTrade"): StatusDomain.ORDER,
    ("order", "SimulateUpdateOrder"): StatusDomain.ORDER,
    ("order", "SimulateUpdateTrade"): StatusDomain.ORDER,
    ("order", "Trade"): StatusDomain.INSTRUCTION,
    ("order", "UpdateOrder"): StatusDomain.INSTRUCTION,
    ("order", "UpdateTrade"): StatusDomain.INSTRUCTION,
    ("order_including_closed", "GetOrderIncludingClosed v2"): StatusDomain.NONE,
    ("pm", "GetHistoricalOrders"): StatusDomain.NONE,
}


def test_get_market_information_spec_matches_docs() -> None:
    assert GET_MARKET_INFORMATION_SPEC.method == "GET"
    # CIAPI serves v2 market data at the documented "/v2/market/..." route under the /TradingAPI
    # base; the catalog's doubled "/market/v2/market/..." path 404s.
    assert (
        GET_MARKET_INFORMATION_SPEC.path
        == "/v2/market/{marketId}/information?clientAccountId={clientAccountId}"
    )
    assert GET_MARKET_INFORMATION_SPEC.auth_policy is AuthPolicy.SESSION
    assert GET_MARKET_INFORMATION_SPEC.idempotent is True
    assert GET_MARKET_INFORMATION_SPEC.response_model is GetMarketInformationResponseDTOv2
    assert [(p.name, p.location, p.python_name) for p in GET_MARKET_INFORMATION_SPEC.params] == [
        ("MarketId", "path", "market_id"),
        ("ClientAccountId", "query", "client_account_id"),
    ]


def test_list_active_orders_spec_matches_docs_and_is_retry_safe() -> None:
    assert LIST_ACTIVE_ORDERS_SPEC.method == "POST"
    assert LIST_ACTIVE_ORDERS_SPEC.path == "/order/activeorders"
    assert LIST_ACTIVE_ORDERS_SPEC.auth_policy is AuthPolicy.SESSION
    assert LIST_ACTIVE_ORDERS_SPEC.idempotent is True
    assert LIST_ACTIVE_ORDERS_SPEC.request_model is ListActiveOrdersRequestDTO
    assert LIST_ACTIVE_ORDERS_SPEC.response_model is ListActiveOrdersResponseDTO
    assert [(p.name, p.location, p.python_name) for p in LIST_ACTIVE_ORDERS_SPEC.params] == [
        ("requestDTO", "body", "request_dto")
    ]


def test_order_v2_specs_use_live_verified_routes() -> None:
    # These three order routes were verified against the live CIAPI demo; the catalog templates
    # (and the prior "/order/v2/..." correction) all 404. They stay base-rooted under /TradingAPI.
    assert (
        GET_ACTIVE_STOP_LIMIT_ORDER_SPEC.path
        == "/order/{orderId}/activeStopLimitOrder?clientAccountId={clientAccountId}"
    )
    assert GET_ACTIVE_STOP_LIMIT_ORDER_SPEC.host_rooted is False
    assert (
        GET_OPEN_POSITION_SPEC.path
        == "/v2/order/{orderId}/openPosition?clientAccountId={clientAccountId}"
    )
    assert SAVE_ORDER_SPEC.method == "POST"
    assert SAVE_ORDER_SPEC.path == "/v2/order"


def test_log_on_spec_matches_docs_and_skips_session_auth() -> None:
    assert LOG_ON_SPEC.method == "POST"
    # CIAPI serves logon from the host root (/v2/session), not under the /TradingAPI base.
    assert LOG_ON_SPEC.path == "/v2/session"
    assert LOG_ON_SPEC.host_rooted is True
    assert LOG_ON_SPEC.auth_policy is AuthPolicy.NONE
    assert LOG_ON_SPEC.idempotent is False
    assert LOG_ON_SPEC.request_model is ApiLogOnRequestDTO
    assert LOG_ON_SPEC.response_model is ApiLogOnResponseDTOv2
    assert [(p.name, p.location, p.python_name) for p in LOG_ON_SPEC.params] == [
        ("apiLogOnRequest", "body", "api_log_on_request")
    ]


def test_get_client_preferences_list_spec_has_no_synthetic_string_param() -> None:
    # The catalog template names its placeholder after the *type* ("keys={string}"), which
    # used to synthesize a bogus required `string` argument and send the filter twice
    # ("keys=" and "Keys="). The _PATH_OVERRIDES entry rebinds the placeholder to Keys.
    assert GET_CLIENT_PREFERENCES_LIST_SPEC.method == "GET"
    assert GET_CLIENT_PREFERENCES_LIST_SPEC.path == (
        "/v2/clientPreference/list?keys={Keys}&clientAccountId={clientAccountId}"
    )
    assert [(p.name, p.location) for p in GET_CLIENT_PREFERENCES_LIST_SPEC.params] == [
        ("Keys", "query"),
        ("ClientAccountId", "query"),
    ]


def test_every_generated_endpoint_has_the_reviewed_status_domain() -> None:
    actual: dict[tuple[str, str], EndpointSpec[Any]] = {}
    for module_name in _endpoints.__all__:
        module = import_module(f"stonepy._endpoints.{module_name}")
        for value in vars(module).values():
            if isinstance(value, EndpointSpec):
                actual[(module_name, value.name)] = value

    # The generator's status-bearing-model guard catches a new carrier DTO; this explicit table
    # pins every currently reviewed carrier endpoint, including reads intentionally set to NONE.
    assert _STATUS_DOMAINS.keys() <= actual.keys()
    for key, spec in actual.items():
        assert spec.status_domain is _STATUS_DOMAINS.get(key, StatusDomain.NONE), key
