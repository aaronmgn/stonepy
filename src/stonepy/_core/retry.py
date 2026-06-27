"""Retry decisions that never double-submit non-idempotent requests."""

from __future__ import annotations

from typing import Any

from stonepy._core.endpoint import EndpointSpec

_RETRYABLE_STATUS = {502, 503, 504}


class RetryPolicy:
    """Retry budget that never auto-resubmits a non-idempotent request.

    Non-idempotent calls (such as placing an order) are never retried automatically, even on a
    transport error, because the original request may have been received: a blind retry could
    double-submit. Idempotent calls retry up to ``max_retries`` times.
    """

    def __init__(self, max_retries: int) -> None:
        self._max = max_retries

    def should_retry(
        self, *, spec: EndpointSpec[Any], response_received: bool, status: int | None, attempt: int
    ) -> bool:
        """Return whether a failed attempt should be retried.

        Args:
            spec: The endpoint being called (its ``idempotent`` flag gates retries).
            response_received: Whether a response arrived (vs a connect/read failure).
            status: The HTTP status when a response arrived, otherwise ``None``.
            attempt: The zero-based attempt that just failed.

        Returns:
            ``True`` only for idempotent calls under the attempt cap, on a transport error or
            a retryable 5xx status (502, 503, 504).
        """
        if attempt >= self._max:
            return False
        if not spec.idempotent:
            return False  # never auto-retry non-idempotent calls (trade safety)
        if not response_received:
            return True  # connect/read error, idempotent -> safe to retry
        return status in _RETRYABLE_STATUS

    def should_retry_rate_limit(self, *, spec: EndpointSpec[Any], attempt: int) -> bool:
        """Return whether a rate-limited (429) idempotent call may be retried again."""
        if attempt >= self._max:
            return False
        return spec.idempotent
