"""Credential-gated probes for audit candidates that need live wire observations.

Read probes make no server changes. Write probes require explicit environment gates and restore
or remove the state they touch. Every candidate uses strict xfail so a confirmed contract is a
loud XPASS that prompts a generator fix.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

import stonepy.models as M
from stonepy import StoneXClient
from stonepy._core.endpoint import Param
from stonepy._endpoints.price_alert import GET_PA_SPEC

pytestmark = pytest.mark.live

_SAVE_PA_GATE = "STONEX_LIVE_SAVE_PA_PROBE"
_MESSAGE_UPDATE_GATE = "STONEX_LIVE_MESSAGE_UPDATE_PROBE"
_PRICE_ALERT_COMMENT = "stonepy-live-audit-save-pa"

ShapeProbe = Callable[[StoneXClient, dict[str, int]], object]


def _md_m5_probes() -> list[Any]:
    screen_name = os.environ.get("STONEX_USERNAME", "stonepy-live-audit")
    return [
        pytest.param(
            lambda client, ids: client.user_account.get_social_actions().community_actions,
            id="community-actions",
        ),
        pytest.param(
            lambda client, ids: client.user_account.get_wall_items_for_users().wall_items_for_users,
            id="wall-items-for-users",
        ),
        pytest.param(
            lambda client, ids: client.user_account.get_wall_sub_items().wall_items,
            id="wall-sub-items",
        ),
        pytest.param(
            lambda client, ids: client.user_account.list_followed(screen_name).following_users,
            id="following-users",
        ),
        pytest.param(
            lambda client, ids: client.user_account.list_followers(screen_name).followed_users,
            id="followed-users",
        ),
        pytest.param(
            lambda client, ids: (
                client.user_account.list_topholders_for_markets(ids["mid"]).top_holders
            ),
            id="top-holders",
        ),
        pytest.param(
            lambda client, ids: _top_holder_users(client, ids["mid"]),
            id="top-holder-users",
        ),
        pytest.param(
            lambda client, ids: (
                client.user_account.get_multiple_users_details_by_client_account_ids().ci_connect_users_details
            ),
            id="multiple-user-details",
        ),
    ]


def _top_holder_users(client: StoneXClient, market_id: int) -> object:
    top_holders = client.user_account.list_topholders_for_markets(market_id).top_holders
    assert top_holders, "live response did not include a top-holder entry"
    return top_holders[0].users


@pytest.mark.xfail(
    reason="MD-M5 catalog array override awaits a confirming live list payload",
    strict=True,
)
@pytest.mark.parametrize("probe", _md_m5_probes())
def test_md_m5_live_shape_candidate(
    client: StoneXClient, ids: dict[str, int], probe: ShapeProbe
) -> None:
    assert isinstance(probe(client, ids), list)


# test_live_round_trips.py:71 already covers SaveUserPreference. Its lines 110-116 also exercise
# GetPA's current body binding, so this read-only probe observes only the query alternative.
@pytest.mark.xfail(
    reason="GetPA query binding is deferred until a live query response confirms it",
    strict=True,
)
def test_get_pa_query_binding_candidate(client: StoneXClient, ids: dict[str, int]) -> None:
    query_spec = replace(
        GET_PA_SPEC,
        params=(
            Param(name="alertId", location="query", python_name="alert_id"),
            Param(
                name="ClientAccountId",
                location="query",
                python_name="client_account_id",
            ),
        ),
    )

    response = client._ctx.invoke(
        query_spec,
        query={"alertId": None, "ClientAccountId": ids["cid"]},
    )

    assert isinstance(response.price_alerts, list)


def _price_alert_request(client: StoneXClient, ids: dict[str, int]) -> M.SaveAlertRequestDTOv2:
    market = client.market.get_market_information(
        market_id=str(ids["mid"]), client_account_id=ids["cid"]
    ).market_information
    assert market is not None and market.prices is not None
    offer = market.prices.offer_price or Decimal("1")
    return M.SaveAlertRequestDTOv2.model_validate(
        {
            "ClientAccountId": ids["cid"],
            "AlertId": 0,
            "MarketId": ids["mid"],
            "Criterion": 1,
            "Direction": 1,
            "FillRate": str(offer * Decimal("1.10")),
            "EmailAddress": "demo@example.com",
            "Expiry": 1,
            "ExpiryDate": None,
            "Comment": _PRICE_ALERT_COMMENT,
            "NotificationMethod": 1,
        }
    )


def _cleanup_price_alert_probe(client: StoneXClient, client_account_id: int) -> None:
    alerts = client.price_alert.get_pa(client_account_id=client_account_id).price_alerts or []
    for alert in alerts:
        if alert.comment == _PRICE_ALERT_COMMENT and alert.alert_id is not None:
            client.price_alert.delete_pa(
                alert_id=alert.alert_id,
                client_account_id=client_account_id,
            )


@pytest.mark.skipif(
    not os.environ.get(_SAVE_PA_GATE),
    reason=f"SavePA probe not enabled (set {_SAVE_PA_GATE}=1)",
)
@pytest.mark.xfail(
    reason="SavePA method and body contract are deferred until an opt-in live confirmation",
    strict=True,
)
def test_save_pa_contract_candidate(client: StoneXClient, ids: dict[str, int]) -> None:
    _cleanup_price_alert_probe(client, ids["cid"])
    try:
        client.price_alert.save_pa(_price_alert_request(client, ids))
        alerts = client.price_alert.get_pa(client_account_id=ids["cid"]).price_alerts or []
        assert any(alert.comment == _PRICE_ALERT_COMMENT for alert in alerts)
    finally:
        _cleanup_price_alert_probe(client, ids["cid"])


@pytest.mark.skipif(
    not os.environ.get(_MESSAGE_UPDATE_GATE),
    reason=f"message update probe not enabled (set {_MESSAGE_UPDATE_GATE}=1)",
)
@pytest.mark.xfail(
    reason="obsolete message-update method and body contract await opt-in live confirmation",
    strict=True,
)
def test_client_communication_message_update_candidate(
    client: StoneXClient, ids: dict[str, int]
) -> None:
    messages = (
        client.message.get_client_communication_messages(ids["cid"]).client_communication_messages
        or []
    )
    message_id = next((message.id for message in messages if message.id is not None), None)
    if message_id is None:
        pytest.xfail("demo account has no client communication message to restore")

    neutral = M.ApiClientCommunicationUpdateRequestDTOv2(
        ClientAccountId=ids["cid"],
        ClientCommunicationId=message_id,
        Accepted=False,
        OtherResponse="",
    )
    try:
        response = client.message.client_communication_message_update(neutral)
    finally:
        # The documented v2 write restores the probe message to a neutral response.
        client.message.save_client_communication_message_response(neutral)

    assert response.success is True
