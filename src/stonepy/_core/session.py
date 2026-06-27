"""Session/token management with single-flight refresh."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from stonepy._core.clock import Clock
from stonepy._core.endpoint import AuthPolicy

SessionRefreshResult: TypeAlias = str | tuple[str, str]


class SessionManager:
    def __init__(self, clock: Clock, proactive_refresh_seconds: float) -> None:
        self._clock = clock
        self._proactive = proactive_refresh_seconds
        self._lock = threading.Lock()
        self._token: str | None = None
        self._username: str = ""
        self._generation = 0
        self._issued_at: float | None = None

    def set_token(self, token: str, username: str) -> None:
        with self._lock:
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()

    async def aset_token(self, token: str, username: str) -> None:
        self.set_token(token, username)

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        with self._lock:
            if policy is AuthPolicy.NONE or self._token is None:
                return {}
            return {"Session": self._token, "UserName": self._username}

    def needs_proactive_refresh(self) -> bool:
        with self._lock:
            if self._issued_at is None:
                return False
            return (self._clock.now() - self._issued_at) >= self._proactive

    def refresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], SessionRefreshResult],
    ) -> None:
        with self._lock:
            if self._generation > seen_generation:
                return  # someone already refreshed; use the new token
            token, username = _refresh_credentials(do_logon(), self._username)
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()


class AsyncSessionManager:
    def __init__(self, clock: Clock, proactive_refresh_seconds: float) -> None:
        self._clock = clock
        self._proactive = proactive_refresh_seconds
        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._username: str = ""
        self._generation = 0
        self._issued_at: float | None = None

    def set_token(self, token: str, username: str) -> None:
        self._token = token
        self._username = username
        self._generation += 1
        self._issued_at = self._clock.now()

    async def aset_token(self, token: str, username: str) -> None:
        async with self._lock:
            self._token = token
            self._username = username
            self._generation += 1
            self._issued_at = self._clock.now()

    @property
    def generation(self) -> int:
        return self._generation

    async def ageneration(self) -> int:
        async with self._lock:
            return self._generation

    def auth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        if policy is AuthPolicy.NONE or self._token is None:
            return {}
        return {"Session": self._token, "UserName": self._username}

    async def aauth_headers(self, policy: AuthPolicy) -> dict[str, str]:
        async with self._lock:
            if policy is AuthPolicy.NONE or self._token is None:
                return {}
            return {"Session": self._token, "UserName": self._username}

    def needs_proactive_refresh(self) -> bool:
        if self._issued_at is None:
            return False
        return (self._clock.now() - self._issued_at) >= self._proactive

    def refresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], SessionRefreshResult],
    ) -> None:
        if self._generation > seen_generation:
            return
        token, username = _refresh_credentials(do_logon(), self._username)
        self._token = token
        self._username = username
        self._generation += 1
        self._issued_at = self._clock.now()

    async def aneeds_proactive_refresh(self) -> bool:
        async with self._lock:
            if self._issued_at is None:
                return False
            return (self._clock.now() - self._issued_at) >= self._proactive

    async def arefresh(
        self,
        seen_generation: int,
        do_logon: Callable[[], Awaitable[SessionRefreshResult]],
    ) -> None:
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
