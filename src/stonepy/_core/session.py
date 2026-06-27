"""Session/token management with single-flight refresh."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from stonepy._core.clock import Clock
from stonepy._core.endpoint import AuthPolicy

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
        call returns without logging on again (single-flight).
        """
        with self._lock:
            if self._generation > seen_generation:
                return  # someone already refreshed; use the new token
            token, username = _refresh_credentials(do_logon(), self._username)
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()


class AsyncSessionManager:
    """Asyncio-safe holder of the current session token with single-flight refresh.

    The awaitable counterpart of [`SessionManager`][stonepy._core.session.SessionManager]; it
    guards its state with an ``asyncio.Lock`` and exposes ``a``-prefixed coroutine variants of
    the read and refresh methods alongside the synchronous ones.
    """

    def __init__(self, clock: Clock, proactive_refresh_seconds: float) -> None:
        self._clock = clock
        self._proactive = proactive_refresh_seconds
        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._username: str = ""
        self._generation = 0
        self._issued_at: float | None = None

    def set_token(self, token: str, username: str) -> None:
        """Store a freshly issued token and username, bumping the generation."""
        self._token = token
        self._username = username
        self._generation += 1
        self._issued_at = self._clock.now()

    async def aset_token(self, token: str, username: str) -> None:
        """Store a freshly issued token and username, bumping the generation."""
        async with self._lock:
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()

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
        """Refresh the token via *do_logon*, unless a peer already advanced the generation.

        ``seen_generation`` is the generation the caller observed before deciding to refresh;
        if the stored generation has moved past it, another caller already refreshed and this
        call returns without logging on again (single-flight).
        """
        if self._generation > seen_generation:
            return
        token, username = _refresh_credentials(do_logon(), self._username)
        self._token = token
        self._username = username
        self._generation += 1
        self._issued_at = self._clock.now()

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
        """Refresh the token via the awaitable *do_logon*, with the same single-flight guard.

        The awaitable twin of [`refresh`][stonepy._core.session.AsyncSessionManager.refresh].
        """
        async with self._lock:
            if self._generation > seen_generation:
                return
            token, username = _refresh_credentials(await do_logon(), self._username)
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
