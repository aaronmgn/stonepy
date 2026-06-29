"""Live read-endpoint checks against the real CIAPI demo account.

Each case calls a generated resource method and asserts the typed response. ``has_data`` cases
must return at least one populated field (so a response-model mismatch that drops the body to
all-``None`` fails loudly); ``ok`` cases only assert the call succeeds and returns its typed
model, because they can legitimately be empty on a fresh demo account.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import stonepy.models as M
from stonepy import StoneXClient

pytestmark = pytest.mark.live

Call = Callable[[StoneXClient, dict[str, int]], Any]

# A recent UTC window (Unix seconds) for the date-range price-history endpoints, computed once at
# collection so the bounds track "now" rather than going stale.
_NOW = datetime.now(UTC)
_FROM_TS = int((_NOW - timedelta(days=3)).timestamp())
_TO_TS = int(_NOW.timestamp())


def _has_data(result: Any) -> bool:
    dump = result.model_dump()
    return any(value not in (None, [], {}) for value in dump.values())


def _ok(result: Any) -> bool:
    return result is not None


# (id, call, check)
READS: list[tuple[str, Call, Callable[[Any], bool]]] = [
    (
        "user_account.get_client_and_trading_account",
        lambda c, i: c.user_account.get_client_and_trading_account(),
        _has_data,
    ),
    (
        "user_account.get_charting_enabled",
        lambda c, i: c.user_account.get_charting_enabled(id=str(i["cid"])),
        _ok,
    ),
    (
        "market.get_market_information",
        lambda c, i: c.market.get_market_information(
            market_id=str(i["mid"]), client_account_id=i["cid"]
        ),
        _has_data,
    ),
    (
        "market.get_market_information_extended",
        lambda c, i: c.market.get_market_information_extended(
            market_id=i["mid"], client_account_id=i["cid"]
        ),
        _has_data,
    ),
    (
        "market.get_market_spread",
        lambda c, i: c.market.get_market_spread(
            client_account_id=str(i["cid"]), market_id=str(i["mid"])
        ),
        _has_data,
    ),
    (
        "market.tag_lookup",
        lambda c, i: c.market.tag_lookup(client_account_id=str(i["cid"])),
        _has_data,
    ),
    (
        "market.list_market_search",
        lambda c, i: c.market.list_market_search(
            search_by_market_code=False,
            search_by_market_name=True,
            spread_product_type=False,
            cfd_product_type=True,
            binary_product_type=False,
            include_options=False,
            query="EUR",
            max_results=5,
            client_account_id=i["cid"],
        ),
        _has_data,
    ),
    (
        "market.get_latest_price_ticks",
        lambda c, i: c.market.get_latest_price_ticks(
            market_id=str(i["mid"]), price_ticks=1, price_type="MID"
        ),
        _has_data,
    ),
    (
        "market.get_price_bars_between_dates",
        lambda c, i: c.market.get_price_bars_between_dates(
            market_id=str(i["mid"]),
            interval="HOUR",
            span=1,
            from_timestamp_utc=_FROM_TS,
            to_timestamp_utc=_TO_TS,
            price_type="MID",
            max_results=5,
        ),
        _ok,
    ),
    (
        "cfd.list_cfd_markets",
        lambda c, i: c.cfd.list_cfd_markets(client_account_id=i["cid"], max_results=5),
        _has_data,
    ),
    (
        "margin.get_client_account_margin",
        lambda c, i: c.margin.get_client_account_margin(client_account_id=i["cid"]),
        _has_data,
    ),
    (
        "watchlist.get_watchlists",
        lambda c, i: c.watchlist.get_watchlists(client_account_id=i["cid"]),
        _has_data,
    ),
    (
        "client_preference.get_client_preferences_key_list",
        lambda c, i: c.client_preference.get_client_preferences_key_list(
            client_account_id=i["cid"]
        ),
        _has_data,
    ),
    (
        "market.list_market_information_search",
        lambda c, i: c.market.list_market_information_search(
            search_by_market_code=False,
            search_by_market_name=True,
            spread_product_type=False,
            cfd_product_type=True,
            binary_product_type=False,
            include_options=False,
            query="EUR",
            trading_account_id=i["tid"],
            max_results=5,
            client_account_id=i["cid"],
        ),
        _has_data,
    ),
    (
        "news.get_news_headlines",
        lambda c, i: c.news.get_news_headlines(region="UK", culture_id=i["culture"]),
        _has_data,
    ),
    (
        "news.get_news",
        lambda c, i: c.news.get_news(region="UK", culture_id=i["culture"]),
        _has_data,
    ),
    (
        "news.get_market_report_headlines",
        lambda c, i: c.news.get_market_report_headlines(
            market_id=i["mid"], culture_id=i["culture"]
        ),
        _has_data,
    ),
    (
        "order.list_active_orders",
        lambda c, i: c.order.list_active_orders(
            M.ListActiveOrdersRequestDTO.model_validate(
                {"TradingAccountId": i["tid"], "MaxResults": 5}
            )
        ),
        _ok,
    ),
    (
        "order.get_orders",
        lambda c, i: c.order.get_orders(client_account_id=str(i["cid"])),
        _ok,
    ),
    (
        "order.get_order_history",
        lambda c, i: c.order.get_order_history(client_account_id=i["cid"]),
        _ok,
    ),
    (
        "order.list_open_positions",
        lambda c, i: c.order.list_open_positions(trading_account_id=i["tid"]),
        _ok,
    ),
    (
        "order.list_active_stop_limit_orders",
        lambda c, i: c.order.list_active_stop_limit_orders(trading_account_id=i["tid"]),
        _ok,
    ),
    (
        "order.list_trade_history",
        lambda c, i: c.order.list_trade_history(trading_account_id=i["tid"]),
        _ok,
    ),
    (
        "spread.list_spread_markets",
        lambda c, i: c.spread.list_spread_markets(
            client_account_id=i["cid"], include_options=False, max_results=5
        ),
        _ok,
    ),
]


# Endpoints whose generated model still mismatches the live wire format (tracked in #24). Marked
# xfail (non-strict) so the suite stays green and flips to a visible xpass once each model is fixed.
_XFAIL: dict[str, str] = {}


def _cases() -> list[Any]:
    params = []
    for name, call, check in READS:
        marks = [pytest.mark.xfail(reason=_XFAIL[name], strict=False)] if name in _XFAIL else []
        params.append(pytest.param(call, check, id=name, marks=marks))
    return params


@pytest.mark.parametrize("call,check", _cases())
def test_live_read(
    client: StoneXClient, ids: dict[str, int], call: Call, check: Callable[[Any], bool]
) -> None:
    result = call(client, ids)
    assert check(result), f"returned no usable data: {result.model_dump()!r}"
