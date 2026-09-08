"""Credential-gated probes for audit candidates that need live wire observations.

All probes require the shared live account guard. Candidate writes have additional opt-in gates.
GetPA creates two temporary alerts to compare both bindings and checks the production binding.
Remaining candidates use restricted strict xfails so unrelated failures stay visible.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

import pytest

import stonepy.models as M
from stonepy import ResponseParseError, StoneXClient, StoneXError
from stonepy._core.endpoint import Param
from stonepy._endpoints.price_alert import GET_PA_SPEC
from tests.live._contract_mismatch import ExpectedLiveContractMismatch, as_contract_mismatch

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
    raises=ExpectedLiveContractMismatch,
)
@pytest.mark.parametrize("probe", _md_m5_probes())
def test_md_m5_live_shape_candidate(
    client: StoneXClient, ids: dict[str, int], probe: ShapeProbe
) -> None:
    try:
        value = probe(client, ids)
    except StoneXError as exc:
        mismatch = as_contract_mismatch(exc)
        if mismatch is None:
            raise
        raise mismatch from exc
    if not isinstance(value, list):
        raise ExpectedLiveContractMismatch(f"expected list, received {type(value).__name__}")


@dataclass(frozen=True)
class _BindingOutcome:
    location: Literal["query", "body"]
    http_ok: bool
    returned_ids: frozenset[int] | None
    error: str | None
    account_filter: str = "unverified"


def _get_pa_binding_outcome(
    client: StoneXClient, ids: dict[str, int], alert_id: int, location: Literal["query", "body"]
) -> _BindingOutcome:
    spec = replace(
        GET_PA_SPEC,
        params=(
            Param("alertId", location, "alert_id"),
            Param("ClientAccountId", location, "client_account_id"),
        ),
    )
    try:
        response = client._ctx.invoke(
            spec, **{location: {"alertId": alert_id, "ClientAccountId": ids["cid"]}}
        )
        alerts = response.price_alerts
        if alerts is None or any(alert.alert_id is None for alert in alerts):
            return _BindingOutcome(location, True, None, "response omitted alerts or alert ids")
        returned_ids = frozenset(alert.alert_id for alert in alerts if alert.alert_id is not None)
        return _BindingOutcome(location, True, returned_ids, None)
    except Exception as exc:
        # Record even unexpected failures so one binding never hides the other's observation.
        http_ok = isinstance(exc, ResponseParseError) and 200 <= exc.http_status < 300
        return _BindingOutcome(location, http_ok, None, repr(exc))


def _delete_probe_alerts(
    client: StoneXClient, client_account_id: int, alert_ids: Sequence[int]
) -> None:
    errors: list[Exception] = []
    for alert_id in alert_ids:
        try:
            removed = client.price_alert.delete_pa(
                alert_id=alert_id, client_account_id=client_account_id
            )
            assert removed is True, f"delete_pa did not delete probe alert {alert_id}"
        except Exception as exc:
            errors.append(exc)
    if errors:
        raise ExceptionGroup("failed to delete probe alerts", errors)


def test_get_pa_selected_binding_honors_filters(client: StoneXClient, ids: dict[str, int]) -> None:
    """Verify query filtering while continuing to observe the catalog body binding.

    Host run 34211196782 on 2026-09-08 returned HTTP 200 for both bindings: query
    honored alertId (9036111), while body returned both run alerts (9036111, 9036112).
    """
    assert [(param.name, param.location) for param in GET_PA_SPEC.params] == [
        ("alertId", "query"),
        ("ClientAccountId", "query"),
    ], "production GetPA must bind both filters to query"
    alert_ids: list[int] = []
    try:
        for _ in range(2):
            saved = client.price_alert.save_price_alert(
                _price_alert_request(client, ids, comment=f"stonepy getpa probe {uuid4().hex}")
            )
            assert saved.alert_id is not None, "save_price_alert did not return an alert id"
            alert_ids.append(saved.alert_id)
        id_a, id_b = alert_ids
        assert id_a != id_b, "GetPA probe requires two distinct alerts"
        outcomes = [
            _get_pa_binding_outcome(client, ids, id_a, location) for location in ("query", "body")
        ]
        print(f"GetPA binding outcomes: {outcomes!r}")
        production_location = GET_PA_SPEC.params[0].location
        selected = next(outcome for outcome in outcomes if outcome.location == production_location)
        assert selected.returned_ids == frozenset({id_a}), (
            f"production GetPA {production_location} binding did not honor alertId: {outcomes!r}"
        )
    finally:
        _delete_probe_alerts(client, ids["cid"], alert_ids)


def _price_alert_request(
    client: StoneXClient, ids: dict[str, int], *, comment: str = _PRICE_ALERT_COMMENT
) -> M.SaveAlertRequestDTOv2:
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
            "Comment": comment,
            "NotificationMethod": 1,
        }
    )


@pytest.mark.skipif(
    not os.environ.get(_SAVE_PA_GATE),
    reason=f"SavePA probe not enabled (set {_SAVE_PA_GATE}=1)",
)
@pytest.mark.xfail(
    reason="SavePA method and body contract are deferred until an opt-in live confirmation",
    strict=True,
    raises=ExpectedLiveContractMismatch,
)
def test_save_pa_contract_candidate(client: StoneXClient, ids: dict[str, int]) -> None:
    """Observe legacy SavePA's update-by-id contract; this probe does not test creation."""
    # Seed a known id through v2; the legacy SavePA response does not resolve an alert id.
    request = _price_alert_request(client, ids, comment=f"stonepy savepa seed {uuid4().hex}")
    alert_id = client.price_alert.save_price_alert(request).alert_id
    assert alert_id is not None, "save_price_alert did not return an alert id"
    try:
        comment = f"stonepy savepa probe {uuid4().hex}"
        update = request.model_copy(update={"alert_id": alert_id, "comment": comment})
        try:
            client.price_alert.save_pa(update)
        except StoneXError as exc:
            mismatch = as_contract_mismatch(exc)
            if mismatch is None:
                raise
            raise mismatch from exc
        alerts = client.price_alert.get_pa(client_account_id=ids["cid"]).price_alerts or []
        assert any(alert.alert_id == alert_id and alert.comment == comment for alert in alerts)
    finally:
        _delete_probe_alerts(client, ids["cid"], [alert_id])


@pytest.mark.skipif(
    not os.environ.get(_MESSAGE_UPDATE_GATE),
    reason=f"message update probe not enabled (set {_MESSAGE_UPDATE_GATE}=1)",
)
@pytest.mark.xfail(
    reason="obsolete message-update method and body contract await opt-in live confirmation",
    strict=True,
    raises=ExpectedLiveContractMismatch,
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
        try:
            response = client.message.client_communication_message_update(neutral)
        except StoneXError as exc:
            mismatch = as_contract_mismatch(exc)
            if mismatch is None:
                raise
            raise mismatch from exc
    finally:
        # The documented v2 write restores the probe message to a neutral response.
        client.message.save_client_communication_message_response(neutral)

    assert response.success is True
