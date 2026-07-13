import asyncio
import threading
from types import TracebackType
from typing import Any

import pytest

from stonepy._core.clock import FakeClock
from stonepy._core.endpoint import AuthPolicy
from stonepy._core.errors import AuthenticationError
from stonepy._core.session import AsyncSessionManager, SessionManager, require_session_token


class _TrackingLock:
    def __init__(self) -> None:
        self.acquisitions = 0

    def __enter__(self) -> None:
        self.acquisitions += 1

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass


class _TrackingAsyncLock:
    def __init__(self) -> None:
        self.acquisitions = 0

    async def __aenter__(self) -> None:
        self.acquisitions += 1

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass


def test_auth_headers_respect_policy() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
    sm.set_token("TOK", "alice")
    assert sm.auth_headers(AuthPolicy.SESSION) == {"Session": "TOK", "UserName": "alice"}
    assert sm.auth_headers(AuthPolicy.NONE) == {}


def test_single_flight_refresh_calls_logon_once_under_concurrency() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
    sm.set_token("OLD", "alice")
    calls = []
    start = threading.Barrier(8)
    seen = sm.generation

    def logon() -> str:
        calls.append(1)
        return "NEW"

    def worker() -> None:
        start.wait()
        sm.refresh(seen, do_logon=logon)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(calls) == 1  # only one re-logon despite 8 concurrent 401s
    assert sm.auth_headers(AuthPolicy.SESSION)["Session"] == "NEW"
    assert sm.generation == seen + 1


def test_refresh_with_stale_generation_does_not_logon_or_overwrite_token() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
    sm.set_token("OLD", "alice")
    stale_generation = sm.generation
    sm.refresh(stale_generation, do_logon=lambda: "NEW")
    calls: list[int] = []

    def logon() -> str:
        calls.append(1)
        return "STALE"

    sm.refresh(stale_generation, do_logon=logon)

    assert calls == []
    assert sm.auth_headers(AuthPolicy.SESSION)["Session"] == "NEW"
    assert sm.generation == stale_generation + 1


def test_refresh_callback_can_update_username_without_prior_token() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)

    sm.refresh(0, do_logon=lambda: ("NEW", "alice"))

    assert sm.auth_headers(AuthPolicy.SESSION) == {"Session": "NEW", "UserName": "alice"}


def test_refresh_with_future_seen_generation_calls_logon() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
    sm.set_token("OLD", "alice")
    calls: list[int] = []

    def logon() -> str:
        calls.append(1)
        return "NEW"

    sm.refresh(seen_generation=2, do_logon=logon)

    assert calls == [1]
    assert sm.auth_headers(AuthPolicy.SESSION)["Session"] == "NEW"
    assert sm.generation == 2


def test_read_paths_take_lock() -> None:
    sm = SessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
    sm.set_token("TOK", "alice")
    lock = _TrackingLock()
    sm_any: Any = sm
    sm_any._lock = lock

    assert sm.generation == 1
    assert sm.auth_headers(AuthPolicy.SESSION) == {"Session": "TOK", "UserName": "alice"}
    assert sm.needs_proactive_refresh() is False
    assert lock.acquisitions == 3


def test_proactive_refresh_after_interval() -> None:
    clk = FakeClock()
    sm = SessionManager(clock=clk, proactive_refresh_seconds=1080)
    sm.set_token("TOK", "alice")
    assert sm.needs_proactive_refresh() is False
    clk.advance(1081)
    assert sm.needs_proactive_refresh() is True


def test_async_session_manager_single_flight_refresh_calls_logon_once() -> None:
    async def run() -> None:
        sm = AsyncSessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
        await sm.aset_token("OLD", "alice")
        calls: list[int] = []
        seen = sm.generation

        async def logon() -> str:
            calls.append(1)
            await asyncio.sleep(0)
            return "NEW"

        await asyncio.gather(*(sm.arefresh(seen, do_logon=logon) for _ in range(8)))

        assert calls == [1]
        assert await sm.aauth_headers(AuthPolicy.SESSION) == {
            "Session": "NEW",
            "UserName": "alice",
        }
        assert sm.generation == seen + 1

    asyncio.run(run())


def test_async_session_read_paths_take_lock() -> None:
    async def run() -> None:
        sm = AsyncSessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)
        await sm.aset_token("TOK", "alice")
        lock = _TrackingAsyncLock()
        sm_any: Any = sm
        sm_any._lock = lock

        assert await sm.ageneration() == 1
        assert await sm.aauth_headers(AuthPolicy.SESSION) == {
            "Session": "TOK",
            "UserName": "alice",
        }
        assert await sm.aneeds_proactive_refresh() is False
        assert lock.acquisitions == 3

    asyncio.run(run())


def test_async_refresh_callback_can_update_username_without_prior_token() -> None:
    async def run() -> None:
        sm = AsyncSessionManager(clock=FakeClock(), proactive_refresh_seconds=1080)

        async def logon() -> tuple[str, str]:
            return ("NEW", "alice")

        await sm.arefresh(0, do_logon=logon)

        assert await sm.aauth_headers(AuthPolicy.SESSION) == {
            "Session": "NEW",
            "UserName": "alice",
        }

    asyncio.run(run())


def test_session_manager_clear_drops_token_and_bumps_generation() -> None:
    manager = SessionManager(FakeClock(), 1080.0)
    manager.set_token("TOKEN", "user")
    generation = manager.generation

    manager.clear()

    assert manager.auth_headers(AuthPolicy.SESSION) == {}
    assert manager.generation == generation + 1
    assert manager.needs_proactive_refresh() is False


def test_async_session_manager_aclear_drops_token() -> None:
    async def run() -> None:
        manager = AsyncSessionManager(FakeClock(), 1080.0)
        await manager.aset_token("TOKEN", "user")

        await manager.aclear()

        assert await manager.aauth_headers(AuthPolicy.SESSION) == {}

    asyncio.run(run())


def test_require_session_token_returns_token() -> None:
    assert require_session_token("TOKEN") == "TOKEN"


def test_require_session_token_raises_on_missing_or_empty() -> None:
    for bad in (None, ""):
        with pytest.raises(AuthenticationError):
            require_session_token(bad)
