"""Business-status domains and decoder types shared by config and pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import TypeAlias


class StatusDomain(Enum):
    """The business-status vocabulary carried by an endpoint response.

    ``NONE`` responses are informational and are never interpreted as placement
    acknowledgements. ``INSTRUCTION`` and ``ORDER`` are numeric lookup-code domains;
    ``EXECUTION_TEXT`` is SaveOrder's closed ``Success``/``Failure`` text domain.
    """

    NONE = "none"
    INSTRUCTION = "instruction"
    ORDER = "order"
    EXECUTION_TEXT = "execution_text"


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
``ClientConfig.status_decoder`` to customize top-level numeric acknowledgement semantics.
"""


class _UnknownInstructionStatus(ValueError):
    """Internal signal that an instruction acknowledgement used an undocumented code."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"unknown InstructionStatus code: {status}")


_OK_STATUS_REASONS = {None, 1}

# Docs/reference/lookup-codes.md defines InstructionStatus as a closed five-value enum.
# RedCard (2) and Error (4) are terminal rejection/error acknowledgements. YellowCard (3) is
# deliberately not a rejection: Docs/reference/guides/Trades.md says a yellow-carded trade is
# sent to the approval queue and may subsequently be accepted or rejected. Treating that interim
# acknowledgement as rejected could prompt a duplicate resubmission while dealer approval is
# still pending. Accepted (1) and Pending (5) likewise pass through.
_INSTRUCTION_STATUSES = frozenset({1, 2, 3, 4, 5})
_INSTRUCTION_REJECTION_STATUSES = frozenset({2, 4})

# Docs/reference/lookup-codes.md defines these OrderStatus values as rejected/blocked. Every
# other lifecycle state -- Pending(1), Accepted(2), Open(3), Cancelled(4), Suspended(6),
# YellowCard(8), Closed(9), Triggered(11), and any future numeric state -- is informational.
# Keeping this set narrow avoids false rejections that could prompt a caller to double an order.
_ORDER_REJECTION_STATUSES = frozenset({5, 10})


def default_status_decoder(status: int, status_reason: int | None) -> StatusDecision:
    """Decode an OrderStatus/OrderStatusReason pair into a rejection decision.

    This callable retains its historical two-argument, order-domain behavior for custom-decoder
    compatibility. The pipeline separately selects instruction-domain decoding for endpoint
    specs marked [`StatusDomain.INSTRUCTION`][stonepy._core.status.StatusDomain].

    Only ``Rejected`` (5) and ``RedCard`` (10) are rejections. Unknown numeric order-lifecycle
    codes are informational rather than rejections. A meaningful reason is resolved from
    ``OrderStatusReason`` first and then the other status-reason enums; otherwise the status name
    is used.
    """
    return _decode_order_status(status, status_reason)


def _decode_default_status(
    domain: StatusDomain, status: int, status_reason: int | None
) -> BusinessStatus:
    """Decode a numeric status with stonepy's domain-specific defaults."""

    if domain is StatusDomain.INSTRUCTION:
        return _decode_instruction_status(status, status_reason)
    if domain is StatusDomain.ORDER:
        return _decode_order_status(status, status_reason)
    raise ValueError(f"numeric status decoder cannot handle {domain.value!r}")


def _decode_instruction_status(status: int, status_reason: int | None) -> BusinessStatus:
    if status not in _INSTRUCTION_STATUSES:
        raise _UnknownInstructionStatus(status)
    if status not in _INSTRUCTION_REJECTION_STATUSES:
        return BusinessStatus(False)
    reason = (
        _decode_status_reason(status_reason, StatusDomain.INSTRUCTION)
        if status_reason not in _OK_STATUS_REASONS
        else _decode_status(status, StatusDomain.INSTRUCTION)
    )
    return BusinessStatus(True, reason)


def _decode_order_status(status: int, status_reason: int | None) -> BusinessStatus:
    if status not in _ORDER_REJECTION_STATUSES:
        return BusinessStatus(False)
    reason = (
        _decode_status_reason(status_reason, StatusDomain.ORDER)
        if status_reason not in _OK_STATUS_REASONS
        else _decode_status(status, StatusDomain.ORDER)
    )
    return BusinessStatus(True, reason)


def _decode_status_reason(status_reason: int | None, domain: StatusDomain) -> str | None:
    if status_reason is None:
        return None
    for enum_cls in _status_reason_enums(domain):
        try:
            return enum_cls(status_reason).name
        except ValueError:
            continue
    return str(status_reason)


def _status_reason_enums(domain: StatusDomain) -> tuple[type[IntEnum], ...]:
    from stonepy.models.enums import (
        InstructionStatusReason,
        OrderStatusReason,
        QuoteStatusReason,
    )

    if domain is StatusDomain.INSTRUCTION:
        return (InstructionStatusReason, OrderStatusReason, QuoteStatusReason)
    if domain is StatusDomain.ORDER:
        return (OrderStatusReason, InstructionStatusReason, QuoteStatusReason)
    raise ValueError(f"numeric status reasons cannot use {domain.value!r}")


def _decode_status(status: int, domain: StatusDomain) -> str:
    for enum_cls in _status_enums(domain):
        try:
            return enum_cls(status).name
        except ValueError:
            continue
    return str(status)


def _status_enums(domain: StatusDomain) -> tuple[type[IntEnum], ...]:
    from stonepy.models.enums import InstructionStatus, OrderStatus, QuoteStatus

    if domain is StatusDomain.INSTRUCTION:
        return (InstructionStatus, OrderStatus, QuoteStatus)
    if domain is StatusDomain.ORDER:
        return (OrderStatus, InstructionStatus, QuoteStatus)
    raise ValueError(f"numeric statuses cannot use {domain.value!r}")
