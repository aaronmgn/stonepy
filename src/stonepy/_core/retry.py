"""Retry decisions that never double-submit non-idempotent requests."""

from __future__ import annotations

from typing import Any

from stonepy._core.endpoint import EndpointSpec

_RETRYABLE_STATUS = {502, 503, 504}


class RetryPolicy:
    def __init__(self, max_retries: int) -> None:
        self._max = max_retries

    def should_retry(
        self, *, spec: EndpointSpec[Any], response_received: bool, status: int | None, attempt: int
    ) -> bool:
        if attempt >= self._max:
            return False
        if not spec.idempotent:
            return False  # never auto-retry non-idempotent calls (trade safety)
        if not response_received:
            return True  # connect/read error, idempotent -> safe to retry
        return status in _RETRYABLE_STATUS

    def should_retry_rate_limit(self, *, spec: EndpointSpec[Any], attempt: int) -> bool:
        if attempt >= self._max:
            return False
        return spec.idempotent
