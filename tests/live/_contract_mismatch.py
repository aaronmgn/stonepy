"""Limit expected live failures to observed contract incompatibilities."""

from __future__ import annotations

from stonepy import AuthenticationError, ResponseParseError, StoneXAPIError


class ExpectedLiveContractMismatch(AssertionError):
    """A response shape or HTTP contract rejection expected by a live audit probe."""


def as_contract_mismatch(exc: BaseException) -> ExpectedLiveContractMismatch | None:
    """Classify parse errors and contract HTTP rejections, excluding authentication.

    Args:
        exc: The exception raised by the candidate endpoint call.

    Returns:
        A restricted mismatch, or ``None`` for failures that must fail the live run.
    """
    if isinstance(exc, ResponseParseError) or (
        isinstance(exc, StoneXAPIError)
        and not isinstance(exc, AuthenticationError)
        and exc.http_status in {400, 404, 405, 415}
    ):
        return ExpectedLiveContractMismatch(repr(exc))
    return None
