"""Session/token management with single-flight refresh."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from stonepy._core.clock import Clock
from stonepy._core.endpoint import AuthPolicy
from stonepy._core.errors import AuthenticationError

SessionRefreshResult: TypeAlias = str | tuple[str, str]
"""A logon result: either a session token, or a ``(token, username)`` pair."""


class SessionManager:
    """Thread-safe holder of the current session token with single-flight refresh.

    Tracks a monotonically increasing ``generation`` so concurrent callers that observe an
    expired token coordinate on a single refresh: a caller whose seen generation is already
    stale skips its own logon and reuses the token a peer just fetched. The
    ``proactive_refresh_seconds`` argument sets how long after issue the token is refreshed
    pre-emptively.
    """

    def __init__(self, clock: Clock, proactive_refresh_seconds: float) -> None:
        self._clock = clock
        self._proactive = proactive_refresh_seconds
        self._lock = threading.Lock()
        self._token: str | None = None
        self._username: str = ""
        self._generation = 0
        self._issued_at: float | None = None
        self._manual_logon: Callable[[], SessionRefreshResult] | None = None

    def commit(
        self, token: str, username: str, do_logon: Callable[[], SessionRefreshResult]
    ) -> None:
        """Install a manual token and its replay callback together under the lock."""
        with self._lock:
            self._token = token
            self._username = username
            self._manual_logon = do_logon
            self._generation += 1
            self._issued_at = self._clock.now()

    def snapshot(self, policy: AuthPolicy) -> tuple[int, dict[str, str]]:
        """Return a coherent generation and independent auth-header copy under one lock."""
        with self._lock:
            headers = (
                {}
                if policy is AuthPolicy.NONE or self._token is None
                else {"Session": self._token, "UserName": self._username}
            )
            return self._generation, headers

    def set_token(self, token: str, username: str) -> None:
        """Store a freshly issued token and username, bumping the generation."""
        with self._lock:
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()

    async def aset_token(self, token: str, username: str) -> None:
        """Store a freshly issued token and username, bumping the generation."""
        self.set_token(token, username)

    def clear(self, expected_token: str | None = None) -> None:
        """Drop the stored token so no auth headers are sent, bumping the generation.

        When *expected_token* is given, the token is only dropped if it is the one currently
        stored; this keeps a log-off aimed at one session (or one that raced a re-logon) from
        discarding a different, still-valid token.
        """
        with self._lock:
            if expected_token is not None and self._token != expected_token:
                return
            self._token = None
            self._username = ""
            self._generation += 1
            self._issued_at = None

    async def aclear(self, expected_token: str | None = None) -> None:
        """Drop the stored token so no auth headers are sent, bumping the generation."""
        self.clear(expected_token)

    @property
    def generation(self) -> int:
        """The current token generation; increments on every refresh."""
        with self._lock:
            return self._generation

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        """Return the session auth headers, or ``{}`` for unauthenticated calls or no token."""
        with self._lock:
            if policy is AuthPolicy.NONE or self._token is None:
                return {}
            return {"Session": self._token, "UserName": self._username}

    def needs_proactive_refresh(self) -> bool:
        """Return whether the token is old enough to refresh before its next use."""
        with self._lock:
            if self._issued_at is None:
                return False
            return (self._clock.now() - self._issued_at) >= self._proactive

    def refresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], SessionRefreshResult],
    ) -> None:
        """Refresh the token via *do_logon*, unless a peer already advanced the generation.

        ``seen_generation`` is the generation the caller observed before deciding to refresh;
        if the stored generation has moved past it, another caller already refreshed and this
        call returns without logging on again (single-flight). Only successful refreshes
        coalesce: failures leave the generation, token, and manual callback unchanged.
        """
        with self._lock:
            if self._generation > seen_generation:
                return  # someone already refreshed; use the new token
            logon = self._manual_logon if self._manual_logon is not None else do_logon
            token, username = _refresh_credentials(logon(), self._username)
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()


class AsyncSessionManager:
    """Asyncio-safe holder of the current session token with single-flight refresh.

    The awaitable counterpart of [`SessionManager`][stonepy._core.session.SessionManager]; it
    guards async operations with an ``asyncio.Lock``. Use ``aset_token``, ``aclear``, and
    ``arefresh`` to mutate tokens; their synchronous twins raise ``TypeError``. Use ``acommit``
    to install a manual token and replay callback together. Synchronous read accessors remain
    available for pipeline helpers.
    """

    def __init__(self, clock: Clock, proactive_refresh_seconds: float) -> None:
        self._clock = clock
        self._proactive = proactive_refresh_seconds
        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._username: str = ""
        self._generation = 0
        self._issued_at: float | None = None
        self._manual_alogon: Callable[[], Awaitable[SessionRefreshResult]] | None = None

    async def acommit(
        self, token: str, username: str, do_logon: Callable[[], Awaitable[SessionRefreshResult]]
    ) -> None:
        """Install a manual token and its replay callback together under the async lock."""
        async with self._lock:
            self._token = token
            self._username = username
            self._manual_alogon = do_logon
            self._generation += 1
            self._issued_at = self._clock.now()

    def snapshot(self, policy: AuthPolicy) -> tuple[int, dict[str, str]]:
        """Return a generation and auth-header copy without taking the async lock.

        This can observe the state before an in-flight refresh completes; prefer
        ``asnapshot`` from async code.
        """
        return self._generation, self.auth_headers(policy)

    async def asnapshot(self, policy: AuthPolicy) -> tuple[int, dict[str, str]]:
        """Return a coherent generation and independent auth-header copy under one lock."""
        async with self._lock:
            return self.snapshot(policy)

    def set_token(self, token: str, username: str) -> None:
        """Reject synchronous mutation, which cannot acquire the async lock.

        Raises:
            TypeError: Always; use ``await manager.aset_token(token, username)`` instead.
        """
        raise TypeError(
            "AsyncSessionManager.set_token() is not supported; "
            "use await manager.aset_token(token, username)"
        )

    async def aset_token(self, token: str, username: str) -> None:
        """Store a freshly issued token and username, bumping the generation."""
        async with self._lock:
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()

    def clear(self, expected_token: str | None = None) -> None:
        """Reject synchronous mutation, which cannot acquire the async lock.

        Raises:
            TypeError: Always; use ``await manager.aclear(expected_token=...)`` instead.
        """
        raise TypeError(
            "AsyncSessionManager.clear() is not supported; "
            "use await manager.aclear(expected_token=...)"
        )

    async def aclear(self, expected_token: str | None = None) -> None:
        """Drop the stored token under the async lock, bumping the generation.

        When *expected_token* is given, the token is only dropped if it is the one currently
        stored; this keeps a log-off aimed at one session (or one that raced a re-logon) from
        discarding a different, still-valid token.
        """
        async with self._lock:
            if expected_token is not None and self._token != expected_token:
                return
            self._token = None
            self._username = ""
            self._generation += 1
            self._issued_at = None

    @property
    def generation(self) -> int:
        """The current token generation; increments on every refresh."""
        return self._generation

    async def ageneration(self) -> int:
        """Return the current token generation under the async lock."""
        async with self._lock:
            return self._generation

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        """Return the session auth headers, or ``{}`` for unauthenticated calls or no token."""
        if policy is AuthPolicy.NONE or self._token is None:
            return {}
        return {"Session": self._token, "UserName": self._username}

    async def aauth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        """Return the session auth headers under the async lock, or ``{}`` if unauthenticated."""
        async with self._lock:
            if policy is AuthPolicy.NONE or self._token is None:
                return {}
            return {"Session": self._token, "UserName": self._username}

    def needs_proactive_refresh(self) -> bool:
        """Return whether the token is old enough to refresh before its next use."""
        if self._issued_at is None:
            return False
        return (self._clock.now() - self._issued_at) >= self._proactive

    def refresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], SessionRefreshResult],
    ) -> None:
        """Reject synchronous refresh without invoking the callback or changing state.

        Raises:
            TypeError: Always; use ``await manager.arefresh(seen_generation, do_logon)``
                with an awaitable logon callback instead.
        """
        raise TypeError(
            "AsyncSessionManager.refresh() is not supported; "
            "use await manager.arefresh(seen_generation, do_logon)"
        )

    async def aneeds_proactive_refresh(self) -> bool:
        """Return whether the token is old enough to refresh, under the async lock."""
        async with self._lock:
            if self._issued_at is None:
                return False
            return (self._clock.now() - self._issued_at) >= self._proactive

    async def arefresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], Awaitable[SessionRefreshResult]],
    ) -> None:
        """Refresh via an awaitable logon unless a peer already advanced the generation.

        ``seen_generation`` is the generation observed before deciding to refresh. A newer
        generation means a peer already refreshed, so this call reuses that token. Only
        successful refreshes coalesce: failures leave the generation, token, and manual callback
        unchanged. A manual callback installed by ``acommit`` takes precedence over *do_logon*.
        """
        async with self._lock:
            if self._generation > seen_generation:
                return
            alogon = self._manual_alogon if self._manual_alogon is not None else do_logon
            token, username = _refresh_credentials(await alogon(), self._username)
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()


def _refresh_credentials(
    result: SessionRefreshResult,
    current_username: str,
) -> tuple[str, str]:
    if isinstance(result, tuple):
        return result
    return result, current_username


def require_session_token(token: str | None) -> str:
    """Return *token*, or raise if a logon reply carried no session token.

    Raises:
        AuthenticationError: When *token* is ``None``, empty, or whitespace-only; storing such
            a token would send a useless ``Session`` header on every later request and surface
            as confusing 401 loops far from the root cause.
    """
    if token and token.strip():
        return token
    raise AuthenticationError(
        http_status=200,
        error_code=None,
        error_message="logon response contained no session token",
        method="POST",
        path="/v2/session",
        raw_body=None,
        headers={},
    )
