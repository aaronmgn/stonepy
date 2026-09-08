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
    start = threading.Barrier(8, timeout=5.0)
    seen = sm.generation

    def logon() -> str:
        calls.append(1)
        return "NEW"

    def worker() -> None:
        start.wait()
        sm.refresh(seen, do_logon=logon)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive(), "thread did not finish: deadlock?"

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

        await asyncio.wait_for(
            asyncio.gather(*(sm.arefresh(seen, do_logon=logon) for _ in range(8))), 5.0
        )

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


@pytest.mark.parametrize(
    "mutation", ["set_token", "clear", "clear_stale", "refresh", "refresh_stale"]
)
def test_sync_mutation_during_async_refresh_raises_without_changing_state(mutation: str) -> None:
    async def run() -> None:
        clock = FakeClock()
        manager = AsyncSessionManager(clock, 1080)
        await manager.aset_token("OLD", "alice")
        generation = manager.generation
        started, release = asyncio.Event(), asyncio.Event()
        sync_logon_calls: list[str] = []

        def sync_logon() -> tuple[str, str]:
            sync_logon_calls.append("called")
            return "SYNC", "eve"

        async def logon() -> tuple[str, str]:
            started.set()
            await release.wait()
            return "REFRESHED", "bob"

        task = asyncio.create_task(manager.arefresh(generation, logon))
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            clock.advance(1081)
            replacement = "a" + mutation.removesuffix("_stale")
            with pytest.raises(TypeError, match=f"await manager.{replacement}"):
                if mutation == "set_token":
                    manager.set_token("SYNC", "eve")
                elif mutation.startswith("refresh"):
                    seen = generation - 1 if mutation == "refresh_stale" else generation
                    manager.refresh(seen, sync_logon)
                else:
                    manager.clear(expected_token="STALE" if mutation == "clear_stale" else None)
            assert sync_logon_calls == []
            assert manager.snapshot(AuthPolicy.SESSION) == (
                generation,
                {"Session": "OLD", "UserName": "alice"},
            )
            assert manager.needs_proactive_refresh() is True
            release.set()
            await asyncio.wait_for(task, timeout=2)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

        assert await manager.asnapshot(AuthPolicy.SESSION) == (
            generation + 1,
            {"Session": "REFRESHED", "UserName": "bob"},
        )
        assert await manager.aneeds_proactive_refresh() is False

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
    for bad in (None, "", "   "):
        with pytest.raises(AuthenticationError):
            require_session_token(bad)


def test_session_manager_clear_with_matching_expected_token_drops_it() -> None:
    manager = SessionManager(FakeClock(), 1080.0)
    manager.set_token("TOKEN", "user")

    manager.clear(expected_token="TOKEN")

    assert manager.auth_headers(AuthPolicy.SESSION) == {}


def test_session_manager_clear_with_stale_expected_token_keeps_current() -> None:
    manager = SessionManager(FakeClock(), 1080.0)
    manager.set_token("NEW", "user")
    generation = manager.generation

    manager.clear(expected_token="OLD")

    assert manager.auth_headers(AuthPolicy.SESSION) == {"Session": "NEW", "UserName": "user"}
    assert manager.generation == generation


def test_async_session_manager_aclear_with_stale_expected_token_keeps_current() -> None:
    async def run() -> None:
        manager = AsyncSessionManager(FakeClock(), 1080.0)
        await manager.aset_token("NEW", "user")

        await manager.aclear(expected_token="OLD")

        assert await manager.aauth_headers(AuthPolicy.SESSION) == {
            "Session": "NEW",
            "UserName": "user",
        }

    asyncio.run(run())


def test_session_snapshot_returns_locked_copy() -> None:
    manager = SessionManager(FakeClock(), 1080)
    manager.set_token("OLD", "alice")
    lock = _TrackingLock()
    manager_any: Any = manager
    manager_any._lock = lock
    generation, headers = manager.snapshot(AuthPolicy.SESSION)
    assert lock.acquisitions == 1
    assert generation == 1 and headers == {"Session": "OLD", "UserName": "alice"}
    headers["Session"] = "OTHER"
    assert manager.snapshot(AuthPolicy.SESSION)[1]["Session"] == "OLD"
    assert manager.snapshot(AuthPolicy.NONE) == (1, {})


def test_async_session_snapshot_returns_locked_copy() -> None:
    async def run() -> None:
        manager = AsyncSessionManager(FakeClock(), 1080)
        await manager.aset_token("OLD", "alice")
        lock = _TrackingAsyncLock()
        manager_any: Any = manager
        manager_any._lock = lock
        generation, headers = await manager.asnapshot(AuthPolicy.SESSION)
        assert lock.acquisitions == 1
        assert generation == 1 and headers == {"Session": "OLD", "UserName": "alice"}
        headers["Session"] = "OTHER"
        assert (await manager.asnapshot(AuthPolicy.SESSION))[1]["Session"] == "OLD"
        assert await manager.asnapshot(AuthPolicy.NONE) == (1, {})

    asyncio.run(run())


class _ManualSession:
    def __init__(self, asynchronous: bool) -> None:
        self.manager = (
            AsyncSessionManager(FakeClock(), 1080)
            if asynchronous
            else SessionManager(FakeClock(), 1080)
        )
        self.calls: list[str] = []

    async def commit(self, token: str) -> None:
        def logon() -> tuple[str, str]:
            self.calls.append(token)
            return token + "-REPLAY", "alice"

        async def alogon() -> tuple[str, str]:
            return logon()

        if isinstance(self.manager, AsyncSessionManager):
            await self.manager.acommit(token, "alice", alogon)
        else:
            self.manager.commit(token, "alice", logon)

    async def refresh(self) -> None:
        def configured() -> tuple[str, str]:
            self.calls.append("CONFIG")
            return "CONFIG", "alice"

        async def aconfigured() -> tuple[str, str]:
            return configured()

        if isinstance(self.manager, AsyncSessionManager):
            await self.manager.arefresh(self.manager.generation, aconfigured)
        else:
            self.manager.refresh(self.manager.generation, configured)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_manual_logon_callback_survives_log_off(asynchronous: bool) -> None:
    async def run() -> None:
        session = _ManualSession(asynchronous)
        await session.commit("MANUAL")
        await session.manager.aclear()
        await session.refresh()
        assert session.calls == ["MANUAL"]
        assert session.manager.auth_headers(AuthPolicy.SESSION)["Session"] == "MANUAL-REPLAY"

    asyncio.run(run())


@pytest.mark.parametrize("asynchronous", [False, True])
def test_second_manual_logon_replaces_callback(asynchronous: bool) -> None:
    async def run() -> None:
        session = _ManualSession(asynchronous)
        await session.commit("FIRST")
        await session.commit("SECOND")
        assert session.manager.auth_headers(AuthPolicy.SESSION)["Session"] == "SECOND"
        await session.refresh()
        assert session.calls == ["SECOND"]

    asyncio.run(run())


@pytest.mark.parametrize("asynchronous", [False, True])
def test_config_logon_is_used_only_without_manual_callback(asynchronous: bool) -> None:
    async def run() -> None:
        session = _ManualSession(asynchronous)
        await session.refresh()
        await session.commit("MANUAL")
        await session.refresh()
        assert session.calls == ["CONFIG", "MANUAL"]

    asyncio.run(run())


@pytest.mark.parametrize("asynchronous", [False, True])
def test_failed_refresh_coalesces_success_only(asynchronous: bool) -> None:
    async def run() -> None:
        session = _ManualSession(asynchronous)
        manager = session.manager
        calls = 0

        def logon() -> tuple[str, str]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("failed logon")
            return "NEW", "alice"

        async def alogon() -> tuple[str, str]:
            await asyncio.sleep(0)
            return logon()

        if isinstance(manager, AsyncSessionManager):
            await manager.acommit("OLD", "alice", alogon)
            callback: object = manager._manual_alogon
        else:
            manager.commit("OLD", "alice", logon)
            callback = manager._manual_logon
        seen = manager.generation
        with pytest.raises(RuntimeError, match="failed logon"):
            await session.refresh()
        assert manager.generation == seen
        assert manager.auth_headers(AuthPolicy.SESSION)["Session"] == "OLD"
        if isinstance(manager, AsyncSessionManager):
            assert manager._manual_alogon is callback
            await asyncio.gather(*(manager.arefresh(seen, alogon) for _ in range(4)))
        else:
            from concurrent.futures import ThreadPoolExecutor

            assert manager._manual_logon is callback
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: manager.refresh(seen, logon), range(4)))
        assert calls == 2
        assert manager.generation == seen + 1
        assert manager.auth_headers(AuthPolicy.SESSION)["Session"] == "NEW"

    asyncio.run(run())
