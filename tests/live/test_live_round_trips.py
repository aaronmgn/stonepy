"""Live write round-trips: create a resource, read it back, then remove it.

Each test cleans up after itself so the demo account is left as it was found. Order placement is
intentionally not round-tripped: it needs ~20 required request fields and a market that accepts a
demo order, which is out of scope for the contract suite.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

import stonepy.models as M
from stonepy import StoneXClient

pytestmark = pytest.mark.live


def test_client_preference_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    test_key = f"STONEPY_LIVE_{uuid4().hex[:8]}"
    cid = ids["cid"]
    request = M.ApiSaveClientPreferenceRequestDTO.model_validate(
        {"ClientAccountId": cid, "ClientPreference": {"Key": test_key, "Value": "1"}}
    )
    client.client_preference.save_client_preference(request)
    try:
        fetched = client.client_preference.get_client_preference(
            client_account_id=cid, key=test_key
        )
        assert fetched is not None
        keys = client.client_preference.get_client_preferences_key_list(client_account_id=cid)
        assert test_key in (keys.client_preference_keys or []), "saved preference key not listed"
        # Live-verify the corrected GetClientPreferencesList binding: lowercase "keys=",
        # sent exactly once (the docs' URI template names the placeholder after its type).
        listed = client.client_preference.get_client_preferences_list([test_key], cid)
        listed_keys = [p.key for p in (listed.client_preferences or [])]
        assert test_key in listed_keys, "keys= filter (lowercase, comma-delimited) not honored"
    finally:
        client.client_preference.delete_client_preference(client_account_id=cid, key=test_key)


def test_watchlist_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    test_watchlist = f"STONEPY_LIVE_{uuid4().hex[:8]}"
    cid = ids["cid"]
    request = M.SaveWatchlistRequestDTO.model_validate(
        {
            "ClientAccountId": cid,
            "Watchlist": {"WatchlistDescription": test_watchlist, "DisplayOrder": 0, "Items": []},
        }
    )
    # Delete by the id the save returns, inside a finally that wraps every post-save step, so the
    # demo account is cleaned up even if the read-back or assertion fails.
    watchlist_id = client.watchlist.save_watchlist(request).watchlist_id
    try:
        assert watchlist_id is not None, "save_watchlist did not return a watchlist id"
        descriptions = [
            w.watchlist_description
            for w in (
                client.watchlist.get_watchlists(client_account_id=cid).client_account_watchlists
                or []
            )
        ]
        assert test_watchlist in descriptions, "created watchlist not found in get_watchlists"
    finally:
        if watchlist_id is not None:
            client.watchlist.delete_watchlist(client_account_id=cid, watchlist_id=watchlist_id)


def test_user_preference_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    test_key = f"STONEPY_LIVE_{uuid4().hex[:8]}"
    # Exercises the DeleteUserPreference param-location fix: the catalog marks Preferences as a body
    # param, but the live API only honors it as a query param (a body request 400s).
    request = M.ApiSavePreferencesRequestDTO.model_validate(
        {"Preferences": [{"Key": test_key, "Value": "1"}]}
    )
    client.preference.save_user_preference(request)
    try:
        result = client.preference.delete_user_preference(preferences=[test_key])
        assert result is not None, "delete_user_preference did not return a response"
    finally:
        # Safety net: ensure the probe key is gone even if the assertion above is later changed.
        client.preference.delete_user_preference(preferences=[test_key])


def test_price_alert_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    # Exercises the DeletePA scalar-response fix: the endpoint returns a bare `true`, so delete_pa
    # must return bool rather than raising a response-parse error.
    cid, mid = ids["cid"], ids["mid"]
    info = client.market.get_market_information(market_id=str(mid), client_account_id=cid)
    assert info.market_information is not None and info.market_information.prices is not None
    offer = info.market_information.prices.offer_price or Decimal("1")
    request = M.SaveAlertRequestDTOv2.model_validate(
        {
            "ClientAccountId": cid,
            "AlertId": 0,
            "MarketId": mid,
            "Criterion": 1,  # AtOrAbove
            "Direction": 1,  # Buy
            "FillRate": str(offer * Decimal("1.10")),
            "EmailAddress": "demo@example.com",
            "Expiry": 1,  # GTC
            "ExpiryDate": None,
            "Comment": "stonepy live round trip",
            "NotificationMethod": 1,  # Email
        }
    )
    alert_id = client.price_alert.save_price_alert(request).alert_id
    try:
        assert alert_id is not None, "save_price_alert did not return an alert id"
        listed = client.price_alert.get_pa(client_account_id=cid).price_alerts or []
        assert any(a.alert_id == alert_id for a in listed), "created alert not found in get_pa"
    finally:
        if alert_id is not None:
            removed = client.price_alert.delete_pa(alert_id=alert_id, client_account_id=cid)
            assert removed is True, "delete_pa should return the bare-scalar success value"
