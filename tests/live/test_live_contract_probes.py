"""Live probes for wire contracts the vendor docs leave ambiguous or unstated.

The scraped documentation is silent or inconsistent on: the logon token's shape (LogOn v2
says "treat as a random string" while DeleteSession declares ``guid minLength 36 maxLength
36``), whether ``LoggedOut`` can be omitted on HTTP 200, and the members/casing of
``ExecutionResponseDTO``'s text ``Status`` enum ("either Success or Failure", never defined).
Each probe pins the observed behavior and fails loudly on drift. Probes never assert secret
values and never place a non-simulation order.
"""

from __future__ import annotations

import os
import uuid
import warnings
from decimal import Decimal

import pytest

import stonepy.models as M
from stonepy import (
    ClientConfig,
    ConfigurationError,
    OrderRejectedError,
    OrderStatusUnknownError,
    StoneXAPIError,
    StoneXClient,
)
from stonepy._core.endpoint import AuthPolicy

pytestmark = pytest.mark.live

_ORDER_PROBE_GATE = "STONEX_LIVE_ORDER_PROBE"


def test_logon_token_shape(client: StoneXClient, ids: dict[str, int]) -> None:
    """Hard-assert only what stonepy relies on (non-blank, unpadded); report the GUID question.

    ``require_session_token`` rejects blank/whitespace tokens; this confirms the live API
    never issues one. Whether tokens are 36-char GUIDs is undocumented for LogOn v2, so a
    mismatch is surfaced as a warning rather than a failure.
    """
    token = client._ctx.session.auth_headers(AuthPolicy.SESSION).get("Session")
    assert token, "authenticated live client has no stored session token"
    assert token == token.strip(), "live logon token has surrounding whitespace"
    try:
        uuid.UUID(token)
    except ValueError:
        warnings.warn(
            f"logon token is not a GUID (length={len(token)}) although the DeleteSession "
            "docs declare its Session parameter as guid/36",
            stacklevel=1,
        )


def test_delete_disposable_session_contract() -> None:
    """Pin the LogOff response shape and the server-side effect of deleting a session.

    The docs say only "true == successful log out" and are silent on omission; stonepy's
    ``is not False`` check assumes an absent flag means success. Uses a dedicated client so
    the session-scoped shared fixture is untouched (it auto-refreshes even if the API allows
    only one session per user).
    """
    config = ClientConfig.from_env()
    with StoneXClient(config) as disposable:
        account = disposable.user_account.get_client_and_trading_account()
        assert account.client_accounts, "logon failed for the disposable session"
        token = disposable._ctx.session.auth_headers(AuthPolicy.SESSION)["Session"]

        response = disposable.session.delete_session(os.environ["STONEX_USERNAME"], token)

        assert response.logged_out is not None, (
            "live API omitted LoggedOut on HTTP 200 - revisit the 'is not False' success "
            "assumption in delete_session"
        )
        assert response.logged_out is True, "valid session delete answered LoggedOut=false"
        assert disposable._ctx.session.auth_headers(AuthPolicy.SESSION) == {}

    # Observed 2026-07-13: the API answered LoggedOut=true but the deleted token kept working
    # immediately afterwards, so server-side invalidation is delayed or absent and cannot be a
    # hard assertion. Observe and report; if the API ever starts rejecting promptly, tighten
    # this back into an assertion.
    with StoneXClient(ClientConfig(base_url=config.base_url)) as stale:
        stale._ctx.session.set_token(token, os.environ["STONEX_USERNAME"])
        try:
            stale.user_account.get_client_and_trading_account()
        except (ConfigurationError, StoneXAPIError):
            warnings.warn(
                "deleted session token was rejected server-side - invalidation now appears "
                "immediate; consider re-tightening this probe into an assertion",
                stacklevel=1,
            )
        else:
            warnings.warn(
                "deleted session token still accepted immediately after LoggedOut=true "
                "(matches 2026-07-13 observation: log-off does not promptly invalidate)",
                stacklevel=1,
            )


@pytest.mark.skipif(
    not os.environ.get(_ORDER_PROBE_GATE),
    reason=f"order probe not enabled (set {_ORDER_PROBE_GATE}=1)",
)
def test_save_order_simulation_text_status_contract(
    client: StoneXClient, ids: dict[str, int]
) -> None:
    """Pin ``ExecutionResponseDTO.Status``'s documented enum ("either Success or Failure").

    The DTO docs define only ``Success`` and ``Failure``. Stonepy treats ``Failure`` as a
    rejection and every other supplied value as indeterminate. This probe sends a
    ``Simulation=True`` order - never a real one - and fails loudly if the live API answers
    outside the documented pair. A rejection also pins the contract: its status must be exactly
    ``"Failure"``.
    """
    request = M.ExecutionVenueRequestDTO(
        ClientAccountId=ids["cid"],
        AppKey=os.environ["STONEX_APP_KEY"],
        RequestId="stonepy-live-order-probe",
        QuoteId=0,
        MarketId=ids["mid"],
        OrderRequests=[
            M.OrderRequestDTO.model_validate(
                {
                    "MarketId": ids["mid"],
                    "Quantity": "1",
                    "OrderDirectionId": 1,
                    "TradingAccountId": ids["tid"],
                }
            )
        ],
        RequestTypeId=1,
        TradingAccountId=ids["tid"],
        UserName=os.environ["STONEX_USERNAME"],
        Simulation=True,
        TransactionId="",
        Bid=Decimal("0"),
        Ask=Decimal("0"),
        AuditId="",
    )
    try:
        response = client.order.save_order(request)
    except OrderRejectedError as exc:
        assert exc.status == "Failure", f"undocumented rejection text status {exc.status!r}"
        return
    except OrderStatusUnknownError as exc:
        pytest.fail(f"undocumented SaveOrder text status {exc.status!r}")
    except StoneXAPIError as exc:
        pytest.xfail(f"probe inconclusive: HTTP-level rejection ({exc.http_status})")
    assert response.status == "Success"
