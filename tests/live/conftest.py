"""Live contract tests: exercise endpoints against the real CIAPI demo account.

These verify the generated client against the live API - catching path, auth, and
response-model mismatches that mocked tests cannot. They are marked ``live`` and skipped unless
``STONEX_USERNAME`` / ``STONEX_PASSWORD`` / ``STONEX_APP_KEY`` are set, so the normal unit-test
run is unaffected. In CI they run nightly and on demand (see ``.github/workflows/live.yml``),
never on pull requests.

Write tests use reversible round-trips and clean up after themselves.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from stonepy import ClientConfig, StoneXClient

_REQUIRED = ("STONEX_USERNAME", "STONEX_PASSWORD", "STONEX_APP_KEY")


def _creds_present() -> bool:
    return all(os.environ.get(name) for name in _REQUIRED)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip every ``live`` test when credentials are not configured."""

    if _creds_present():
        return
    skip = pytest.mark.skip(reason="live credentials not set (STONEX_USERNAME/PASSWORD/APP_KEY)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def client() -> Iterator[StoneXClient]:
    """A live, authenticated client built from the ``STONEX_*`` environment."""

    with StoneXClient(ClientConfig.from_env()) as live_client:
        yield live_client


@pytest.fixture(scope="session")
def ids(client: StoneXClient) -> dict[str, int]:
    """Bootstrap the account/market identifiers the live tests need, via the typed client.

    This exercises the account and CFD-market reads as a side effect: if either response model
    regresses, every dependent live test fails at setup.
    """

    account = client.user_account.get_client_and_trading_account()
    assert account.client_accounts, "demo account returned no client accounts"
    assert account.trading_accounts, "demo account returned no trading accounts"
    client_account = account.client_accounts[0]
    cid = client_account.client_account_id
    tid = account.trading_accounts[0].trading_account_id
    assert cid is not None and tid is not None, "demo account is missing required ids"

    market_list = client.cfd.list_cfd_markets(client_account_id=cid, max_results=5).markets or []
    assert market_list, "demo account returned no CFD markets"
    mid = market_list[0].market_id
    assert mid is not None, "CFD market is missing its id"

    party = account.legal_parties[0].party_id if account.legal_parties else None
    operator = (
        account.account_operators[0].account_operator_id if account.account_operators else None
    )
    return {
        "cid": cid,
        "tid": tid,
        "culture": client_account.culture_id or 9,
        "party": party or 0,
        "operator": operator or 0,
        "mid": mid,
    }
