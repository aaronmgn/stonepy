"""Explicit opt-in and account-target checks shared by live tests."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from urllib.parse import urlsplit

from stonepy import ClientConfig, StoneXClient
from stonepy.models import AccountResult

DEMO_HOST_ALLOWLIST: frozenset[tuple[str, int | None]] = frozenset(
    {
        ("ciapi.cityindex.com", None),
        ("ciapi.cityindex.com", 443),
        ("ciapipreprod.cityindextest9.co.uk", None),
        ("ciapipreprod.cityindextest9.co.uk", 443),
        ("ciapipreprod.cityindextest9.co.uk", 8443),
    }
)
REQUIRED_VARIABLES = (
    "STONEX_USERNAME",
    "STONEX_PASSWORD",
    "STONEX_APP_KEY",
    "STONEX_LIVE_CLIENT_ACCOUNT_ID",
)


def live_tests_enabled(environ: Mapping[str, str]) -> bool:
    """Return whether explicit opt-in and all required live settings are present."""
    return not missing_live_requirements(environ)


def missing_live_requirements(environ: Mapping[str, str]) -> list[str]:
    """List the opt-in and variable names needed to enable live tests."""
    missing = [] if environ.get("STONEX_LIVE") == "1" else ["STONEX_LIVE=1"]
    missing.extend(name for name in REQUIRED_VARIABLES if not environ.get(name, "").strip())
    return missing


def validate_live_target(base_url: str) -> None:
    """Require HTTPS on an exact allowlisted host and port without user information.

    Args:
        base_url: Configured live API base URL.

    Raises:
        ValueError: The target is invalid; the message includes only its hostname.
    """
    hostname = "(missing)"
    try:
        parsed = urlsplit(base_url)
        hostname = (parsed.hostname or hostname).lower()
        approved = (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and (hostname, parsed.port) in DEMO_HOST_ALLOWLIST
            and not any(char.isspace() for char in base_url)
        )
    except ValueError:
        approved = False
    if not approved:
        raise ValueError(f"live target hostname {hostname!r} is not approved") from None


def expected_client_account_id(environ: Mapping[str, str]) -> int:
    """Read the approved positive client-account id.

    Args:
        environ: Environment containing ``STONEX_LIVE_CLIENT_ACCOUNT_ID``.

    Returns:
        The approved client-account identifier.

    Raises:
        ValueError: The identifier is missing or is not a positive integer.
    """
    try:
        account_id = int(environ.get("STONEX_LIVE_CLIENT_ACCOUNT_ID", ""))
    except ValueError:
        account_id = 0
    if account_id <= 0:
        raise ValueError("STONEX_LIVE_CLIENT_ACCOUNT_ID must be a positive integer")
    return account_id


@contextmanager
def live_client(environ: Mapping[str, str]) -> Iterator[StoneXClient]:
    """Open a client only after validating the configured live target.

    Args:
        environ: Environment containing the live target and credentials.

    Yields:
        A client whose configured host and port are approved for live tests.
    """
    base_url = environ.get("STONEX_BASE_URL", "")
    validate_live_target(base_url)
    config = ClientConfig(
        base_url=base_url,
        username=environ.get("STONEX_USERNAME", ""),
        password=environ.get("STONEX_PASSWORD", ""),
        app_key=environ.get("STONEX_APP_KEY", ""),
    )
    with StoneXClient(config) as client:
        yield client


def approved_live_account(client: StoneXClient, environ: Mapping[str, str]) -> AccountResult:
    """Read the account and require its first client id to match the approved id.

    Args:
        client: Client connected to an approved live target.
        environ: Environment containing the approved client-account identifier.

    Returns:
        The verified account details for subsequent live tests.

    Raises:
        AssertionError: The response omits client accounts or the first id is not approved.
    """
    expected = expected_client_account_id(environ)
    account = client.user_account.get_client_and_trading_account()
    assert account.client_accounts, "demo account returned no client accounts"
    observed = account.client_accounts[0].client_account_id
    assert observed == expected, (
        f"live account {observed} is not the approved STONEX_LIVE_CLIENT_ACCOUNT_ID {expected}"
    )
    return account
