from __future__ import annotations

from stonepy._core.endpoint import AuthPolicy
from stonepy._endpoints.market import GET_MARKET_INFORMATION_SPEC
from stonepy._endpoints.order import LIST_ACTIVE_ORDERS_SPEC
from stonepy._endpoints.session import LOG_ON_SPEC
from stonepy.models import (
    ApiLogOnRequestDTO,
    ApiLogOnResponseDTOv2,
    GetMarketInformationResponseDTOv2,
    ListActiveOrdersRequestDTO,
    ListActiveOrdersResponseDTO,
)


def test_get_market_information_spec_matches_docs() -> None:
    assert GET_MARKET_INFORMATION_SPEC.method == "GET"
    assert (
        GET_MARKET_INFORMATION_SPEC.path
        == "/market/v2/market/{marketId}/information?clientAccountId={clientAccountId}"
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
        ("requestDTO", "query", "request_dto")
    ]


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
