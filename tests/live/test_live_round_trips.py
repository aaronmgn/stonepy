"""Live write round-trips: create a resource, read it back, then remove it.

Each test cleans up after itself so the demo account is left as it was found. Order placement is
intentionally not round-tripped: it needs ~20 required request fields and a market that accepts a
demo order, which is out of scope for the contract suite.
"""

from __future__ import annotations

import pytest

import stonepy.models as M
from stonepy import StoneXClient

pytestmark = pytest.mark.live

_TEST_KEY = "STONEPY_LIVE_ROUND_TRIP"
_TEST_WATCHLIST = "stonepy-live-round-trip"


def test_client_preference_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    cid = ids["cid"]
    request = M.ApiSaveClientPreferenceRequestDTO.model_validate(
        {"ClientAccountId": cid, "ClientPreference": {"Key": _TEST_KEY, "Value": "1"}}
    )
    client.client_preference.save_client_preference(request)
    try:
        fetched = client.client_preference.get_client_preference(
            client_account_id=cid, key=_TEST_KEY
        )
        assert fetched is not None
        keys = client.client_preference.get_client_preferences_key_list(client_account_id=cid)
        assert _TEST_KEY in (keys.client_preference_keys or []), "saved preference key not listed"
    finally:
        client.client_preference.delete_client_preference(client_account_id=cid, key=_TEST_KEY)


def test_watchlist_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    cid = ids["cid"]
    request = M.SaveWatchlistRequestDTO.model_validate(
        {
            "ClientAccountId": cid,
            "Watchlist": {"WatchlistDescription": _TEST_WATCHLIST, "DisplayOrder": 0, "Items": []},
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
        assert _TEST_WATCHLIST in descriptions, "created watchlist not found in get_watchlists"
    finally:
        if watchlist_id is not None:
            client.watchlist.delete_watchlist(client_account_id=cid, watchlist_id=watchlist_id)
