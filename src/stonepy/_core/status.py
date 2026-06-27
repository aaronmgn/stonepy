"""Business-status decoder types shared by config and pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TypeAlias


@dataclass(frozen=True)
class BusinessStatus:
    """A decoded business-status decision for an order response.

    Attributes:
        is_rejection: Whether the status means the order was rejected or blocked.
        reason: A human-readable rejection reason, when one is known.
    """

    is_rejection: bool
    reason: str | None = None


StatusDecision: TypeAlias = BusinessStatus | bool | str | None
"""A decoder's verdict for a status/reason pair.

Either a [`BusinessStatus`][stonepy._core.status.BusinessStatus], a bare ``bool`` (rejected or
not), a ``str`` (rejected, with that reason), or ``None`` (not a rejection).
"""

StatusDecoder: TypeAlias = Callable[[int, int | None], StatusDecision]
"""A callable mapping ``(status, status_reason)`` to a
[`StatusDecision`][stonepy._core.status.StatusDecision]. Override
``ClientConfig.status_decoder`` to customize order-rejection semantics.
"""


_OK_STATUS_REASONS = {None, 1}
# OrderStatus values that mean the order was rejected/blocked (OrderStatus.Rejected=5,
# OrderStatus.RedCard=10). Every other lifecycle state — Pending(1), Accepted(2), Open(3),
# Cancelled(4), Suspended(6), YellowCard(8), Closed(9), Triggered(11) — is a normal, working,
# or closed outcome, not a rejection. The Status is authoritative; the StatusReason only
# supplies the human-readable reason when a rejection is raised. Keeping this set narrow avoids
# false rejections, which in a trading client could prompt a caller to resubmit and double an
# order. Callers needing different semantics can override ``ClientConfig.status_decoder``.
_REJECTION_STATUSES = {5, 10}


def default_status_decoder(status: int, status_reason: int | None) -> StatusDecision:
    """Decode an order ``Status``/``StatusReason`` pair into a rejection decision.

    Treats only ``Rejected`` (5) and ``RedCard`` (10) as rejections; every other lifecycle
    state is a normal outcome. The reason is resolved from the ``StatusReason`` enums when a
    meaningful reason is present (not ``None`` and not the generic OK code ``1``); otherwise it
    falls back to the status name. Kept deliberately narrow so a working order is never mistaken
    for a rejection (which could prompt a caller to resubmit and double up).
    """
    if status not in _REJECTION_STATUSES:
        return BusinessStatus(False)
    reason = (
        _decode_status_reason(status_reason)
        if status_reason not in _OK_STATUS_REASONS
        else _decode_status(status)
    )
    return BusinessStatus(True, reason)


def _decode_status_reason(status_reason: int | None) -> str | None:
    if status_reason is None:
        return None
    for enum_cls in _status_reason_enums():
        try:
            return enum_cls(status_reason).name
        except ValueError:
            continue
    return str(status_reason)


def _status_reason_enums() -> tuple[type[IntEnum], ...]:
    from stonepy.models.enums import (
        InstructionStatusReason,
        OrderStatusReason,
        QuoteStatusReason,
    )

    return (OrderStatusReason, InstructionStatusReason, QuoteStatusReason)


def _decode_status(status: int) -> str | None:
    for enum_cls in _status_enums():
        try:
            return enum_cls(status).name
        except ValueError:
            continue
    return str(status)


def _status_enums() -> tuple[type[IntEnum], ...]:
    from stonepy.models.enums import (
        InstructionStatus,
        OrderStatus,
        QuoteStatus,
    )

    return (OrderStatus, QuoteStatus, InstructionStatus)
