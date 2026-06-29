"""Live write round-trips: create a resource, read it back, then remove it.

Each test cleans up after itself so the demo account is left as it was found. Order placement is
intentionally not round-tripped yet: it needs ~20 required request fields and the order read
models (``get_orders``/``list_open_positions``) are currently broken, so a placed order cannot be
verified through the client. That round-trip is unblocked once the order response models are fixed.
"""

from __future__ import annotations

import pytest

import stonepy.models as M
from stonepy import StoneXClient

pytestmark = pytest.mark.live

_TEST_KEY = "STONEPY_LIVE_ROUND_TRIP"
_TEST_WATCHLIST = "stonepy-live-round-trip"


@pytest.mark.xfail(
    reason="ApiSaveClientPreferenceRequestDTO.ClientPreference typed as a list but the API expects "
    "a single ClientPreferenceKeyDTO, so Save returns 400 (#24)",
    strict=False,
)
def test_client_preference_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    cid = ids["cid"]
    request = M.ApiSaveClientPreferenceRequestDTO.model_validate(
        {"ClientAccountId": cid, "ClientPreference": [{"Key": _TEST_KEY, "Value": "1"}]}
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


@pytest.mark.xfail(
    reason="SaveWatchlistRequestDTO is rejected with HTTP 400 by /v2/watchlists/save - request "
    "model does not match what the API expects (#24)",
    strict=False,
)
def test_watchlist_round_trip(client: StoneXClient, ids: dict[str, int]) -> None:
    cid = ids["cid"]
    request = M.SaveWatchlistRequestDTO.model_validate(
        {"ClientAccountId": cid, "Watchlist": [{"WatchlistDescription": _TEST_WATCHLIST}]}
    )
    client.watchlist.save_watchlist(request)
    created = [
        w
        for w in (
            client.watchlist.get_watchlists(client_account_id=cid).client_account_watchlists or []
        )
        if w.watchlist_description == _TEST_WATCHLIST
    ]
    try:
        assert created, "created watchlist not found in get_watchlists"
    finally:
        for watchlist in created:
            if watchlist.watchlist_id is not None:
                client.watchlist.delete_watchlist(
                    client_account_id=cid, watchlist_id=watchlist.watchlist_id
                )
