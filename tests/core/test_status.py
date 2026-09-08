"""Unit tests for the default business-status decoder.

OrderStatus lifecycle (from the catalog enum): Pending=1, Accepted=2, Open=3, Cancelled=4,
Rejected=5, Suspended=6, YellowCard=8, Closed=9, RedCard=10, Triggered=11. Only Rejected and
RedCard mean the order was rejected; every other state is a normal/working/closed outcome. The
default decoder must NOT raise on the non-rejection states (a false rejection could make a caller
resubmit and double an order).
"""

from __future__ import annotations

import pytest

from stonepy._core.status import BusinessStatus, default_status_decoder

_NON_REJECTION_STATUSES = [1, 2, 3, 4, 6, 8, 9, 11]
_REJECTION_STATUSES = [5, 10]


def _decode(status: int, status_reason: int | None) -> BusinessStatus:
    decision = default_status_decoder(status, status_reason)
    assert isinstance(decision, BusinessStatus)
    return decision


@pytest.mark.parametrize("status", _NON_REJECTION_STATUSES)
def test_non_rejection_statuses_are_not_rejections(status: int) -> None:
    assert _decode(status, 1).is_rejection is False, f"status {status} wrongly flagged rejected"


def test_accepted_with_non_ok_reason_is_still_not_a_rejection() -> None:
    # Status is authoritative: an Accepted (or any non-rejection) order is not a rejection,
    # whatever the accompanying StatusReason.
    assert _decode(2, 42).is_rejection is False


@pytest.mark.parametrize("status", _REJECTION_STATUSES)
def test_rejected_and_redcard_statuses_are_rejections(status: int) -> None:
    assert _decode(status, 1).is_rejection is True


def test_rejection_reason_prefers_status_reason_then_falls_back_to_status_name() -> None:
    assert _decode(5, 42).reason == "OrdersinOCOPairmustbeeitherStoporLimit"
    assert _decode(5, 1).reason == "Rejected"
    assert _decode(10, None).reason == "RedCard"
    assert _decode(5, 9999).reason == "9999"


def test_positional_only_legacy_decoder_is_called_with_two_arguments() -> None:
    from stonepy._core.status import StatusDomain, normalize_status_decoder

    def legacy(status: int, reason: int | None, /) -> str:
        return f"{status}:{reason}"

    decoder = normalize_status_decoder(legacy)
    assert decoder is not None
    assert decoder(2, None, domain=StatusDomain.INSTRUCTION) == "2:None"


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_uninspectable_status_decoder_falls_back_to_two_arguments(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    import inspect

    from stonepy._core import status as status_module

    def uninspectable(obj: object) -> None:
        raise error_type("no signature")

    monkeypatch.setattr(inspect, "signature", uninspectable)
    decoder = status_module.normalize_status_decoder(lambda status, reason: str(status))
    assert decoder is not None
    assert decoder(1, None, domain=status_module.StatusDomain.ORDER) == "1"


def test_invalid_status_decoder_signature_is_rejected() -> None:
    from typing import cast

    from stonepy._core.status import LegacyStatusDecoder, normalize_status_decoder

    with pytest.raises(TypeError, match="status_decoder must accept"):
        normalize_status_decoder(cast(LegacyStatusDecoder, lambda: None))
