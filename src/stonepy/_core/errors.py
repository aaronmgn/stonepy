"""Exception hierarchy for stonepy."""

from __future__ import annotations

from collections.abc import Mapping

_REDACT = {"session", "password", "appkey", "authorization"}


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {k: ("***" if k.lower() in _REDACT else v) for k, v in headers.items()}


class StoneXError(Exception):
    """Base class for all stonepy errors."""


class StoneXAPIError(StoneXError):
    """HTTP or API business-error response with endpoint context.

    `raw_body` is retained for diagnostics and may contain sensitive response data.
    It is intentionally omitted from `str()` and redacted from `repr()`.
    """

    def __init__(
        self,
        *,
        http_status: int,
        error_code: int | None,
        error_message: str | None,
        method: str,
        path: str,
        raw_body: bytes | None,
        headers: Mapping[str, str],
    ) -> None:
        self.http_status = http_status
        self.error_code = error_code
        self.error_message = error_message
        self.method = method
        self.path = path
        self.raw_body = raw_body
        self.headers = dict(headers)
        super().__init__(
            f"{method} {path} -> HTTP {http_status} (ErrorCode={error_code}): {error_message}"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(http_status={self.http_status}, "
            f"error_code={self.error_code}, method={self.method!r}, "
            f"path={self.path!r}, headers={_safe_headers(self.headers)!r})"
        )


class AuthenticationError(StoneXAPIError):
    """Invalid credentials (ErrorCode 4010) or unrecoverable 401."""


class ResponseParseError(StoneXError):
    """Malformed or schema-invalid success response body.

    `raw_body` is retained for diagnostics and may contain sensitive response data.
    It is intentionally omitted from `str()` and redacted from `repr()`.
    """

    def __init__(
        self,
        *,
        phase: str,
        http_status: int,
        method: str,
        path: str,
        raw_body: bytes,
        message: str,
    ) -> None:
        self.phase = phase
        self.http_status = http_status
        self.method = method
        self.path = path
        self.raw_body = raw_body
        super().__init__(
            f"{method} {path} -> HTTP {http_status} response {phase} failed: {message}"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(phase={self.phase!r}, "
            f"http_status={self.http_status}, method={self.method!r}, path={self.path!r}, "
            f"raw_body=<redacted {len(self.raw_body)} bytes>)"
        )


class RateLimitError(StoneXAPIError):
    """Rate-limit API error with an optional parsed retry_after delay."""

    def __init__(
        self,
        *,
        http_status: int,
        error_code: int | None,
        error_message: str | None,
        method: str,
        path: str,
        raw_body: bytes | None,
        headers: Mapping[str, str],
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            http_status=http_status,
            error_code=error_code,
            error_message=error_message,
            method=method,
            path=path,
            raw_body=raw_body,
            headers=headers,
        )


class OrderRejectedError(StoneXError):
    """Order business-status rejection with optional endpoint context.

    `response` is retained for diagnostics and may contain sensitive response data.
    It is intentionally omitted from `repr()`.
    """

    def __init__(
        self,
        *,
        status: int,
        status_reason: int | None,
        reason: str | None,
        response: object,
        method: str | None = None,
        path: str | None = None,
        http_status: int | None = None,
    ) -> None:
        self.status = status
        self.status_reason = status_reason
        self.reason = reason
        self.response = response
        self.method = method
        self.path = path
        self.http_status = http_status
        endpoint = f"{method} {path} -> HTTP {http_status}: " if method and path else ""
        super().__init__(f"{endpoint}Order rejected: status={status} reason={reason!r}")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status}, "
            f"status_reason={self.status_reason}, reason={self.reason!r}, "
            f"method={self.method!r}, path={self.path!r}, http_status={self.http_status})"
        )


class TransportError(StoneXError):
    """Network-level failure (connect/read/timeout)."""

    def __init__(self, message: str, *, method: str, path: str, attempt: int) -> None:
        self.method = method
        self.path = path
        self.attempt = attempt
        super().__init__(f"{method} {path} transport failed on attempt {attempt}: {message}")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(method={self.method!r}, path={self.path!r}, "
            f"attempt={self.attempt})"
        )
