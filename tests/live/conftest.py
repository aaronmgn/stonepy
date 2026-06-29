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
from urllib.parse import urlsplit

import httpx
import pytest

from stonepy import ClientConfig, StoneXClient

_REQUIRED = ("STONEX_USERNAME", "STONEX_PASSWORD", "STONEX_APP_KEY")
_DEFAULT_BASE = "https://ciapi.cityindex.com/TradingAPI"


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
def ids() -> dict[str, int]:
    """Bootstrap the account/market identifiers the live tests need.

    Fetched with a raw request rather than the typed client because the v2 account endpoint's
    response model wraps its body in ``account_result`` while the API returns the fields flat,
    so the typed client cannot currently read the ids (tracked as a known response-model bug).
    """

    base = os.environ.get("STONEX_BASE_URL", _DEFAULT_BASE)
    parts = urlsplit(base)
    host = f"{parts.scheme}://{parts.netloc}"
    user = os.environ["STONEX_USERNAME"]
    with httpx.Client(timeout=30.0) as http:
        token = http.post(
            f"{host}/v2/session",
            json={
                "UserName": user,
                "Password": os.environ["STONEX_PASSWORD"],
                "AppKey": os.environ["STONEX_APP_KEY"],
            },
        ).json()
        token = token.get("session") or token.get("Session")
        headers = {"UserName": user, "Session": token}
        acct = http.get(f"{host}/v2/UserAccount/ClientAndTradingAccount", headers=headers).json()
        client_account = acct["clientAccounts"][0]
        cid = client_account["clientAccountId"]
        markets = http.get(
            f"{base}/cfd/markets",
            headers=headers,
            params={"MarketName": "", "MaxResults": 5, "ClientAccountId": cid},
        ).json()
        market_list = markets.get("Markets") or markets.get("markets") or []
        market = market_list[0] if market_list else {}
    return {
        "cid": cid,
        "tid": acct["tradingAccounts"][0]["tradingAccountId"],
        "culture": client_account.get("cultureId", 9),
        "party": acct["legalParties"][0]["partyId"],
        "operator": acct["accountOperators"][0]["accountOperatorId"],
        "mid": market.get("MarketId") or market.get("marketId"),
    }
