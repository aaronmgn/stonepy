from __future__ import annotations

import asyncio
import re
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import cast

import pytest

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy._core.pipeline import CallContext
from stonepy._core.resource import BaseResource

_ALIASES = [
    ("clientapplication", "client_application"),
    ("fixedmargin", "fixed_margin"),
    ("tradingadvisor", "trading_advisor"),
]
_RESOURCE_NAMES = [
    name
    for name, value in vars(StoneXClient).items()
    if isinstance(value, property)
    and name not in {"call_context", "order_including_closed", *(old for old, _ in _ALIASES)}
]


def _with_client(
    async_client: bool, check: Callable[[StoneXClient | AsyncStoneXClient], None]
) -> None:
    config = ClientConfig(base_url="https://api.example")
    if async_client:

        async def run() -> None:
            async with AsyncStoneXClient(config) as client:
                check(client)

        asyncio.run(run())
    else:
        with StoneXClient(config) as client:
            check(client)


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("resource_name", _RESOURCE_NAMES)
def test_concurrent_first_access_constructs_one_resource(
    monkeypatch: pytest.MonkeyPatch, async_client: bool, resource_name: str
) -> None:
    constructed: list[BaseResource] = []
    original = BaseResource.__init__

    def build(self: BaseResource, ctx: CallContext) -> None:
        constructed.append(self)
        # Release the GIL inside construction so an unguarded property reliably races.
        time.sleep(0.01)
        original(self, ctx)

    monkeypatch.setattr(BaseResource, "__init__", build)

    def check(client: StoneXClient | AsyncStoneXClient) -> None:
        assert not constructed  # Construction remains lazy.
        barrier = Barrier(8)

        def access(_: int) -> BaseResource:
            barrier.wait(timeout=5)
            return cast(BaseResource, getattr(client, resource_name))

        with ThreadPoolExecutor(max_workers=8) as pool:
            resources = list(pool.map(access, range(8)))
        assert len(constructed) == 1
        assert all(resource is constructed[0] for resource in resources)
        assert getattr(client, resource_name) is constructed[0]
        assert constructed[0].call_context is client.call_context

    _with_client(async_client, check)


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(("legacy", "canonical"), _ALIASES)
def test_canonical_resource_aliases_share_instances(
    async_client: bool, legacy: str, canonical: str
) -> None:
    def check(client: StoneXClient | AsyncStoneXClient) -> None:
        # Access the old property first too, to cover lazy construction through either spelling.
        with pytest.warns(DeprecationWarning, match=re.escape(legacy)) as caught:
            access_line = sys._getframe().f_lineno + 1
            old = getattr(client, legacy)
        assert len(caught) == 1
        assert (caught[0].filename, caught[0].lineno) == (__file__, access_line)
        assert old is getattr(client, canonical)
        assert getattr(client, canonical) is getattr(client, canonical)
        assert getattr(client, "_" + canonical) is old

    _with_client(async_client, check)


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(("legacy", "canonical"), _ALIASES)
def test_legacy_resource_names_warn(async_client: bool, legacy: str, canonical: str) -> None:
    def check(client: StoneXClient | AsyncStoneXClient) -> None:
        message = f"{type(client).__name__}.{legacy} is deprecated; use {canonical}"
        for _ in range(2):
            with pytest.warns(DeprecationWarning, match=f"^{re.escape(message)}$") as caught:
                access_line = sys._getframe().f_lineno + 1
                getattr(client, legacy)
            assert len(caught) == 1
            assert (caught[0].filename, caught[0].lineno) == (__file__, access_line)

    _with_client(async_client, check)


@pytest.mark.parametrize("async_client", [False, True], ids=["sync", "async"])
def test_legacy_order_including_closed_group_warns(async_client: bool) -> None:
    def check(client: StoneXClient | AsyncStoneXClient) -> None:
        message = (
            f"{type(client).__name__}.order_including_closed is deprecated; "
            "use client.order.get_order_including_closed"
        )
        with pytest.warns(DeprecationWarning, match=f"^{re.escape(message)}$") as caught:
            access_line = sys._getframe().f_lineno + 1
            resource = client.order_including_closed
        assert len(caught) == 1
        assert (caught[0].filename, caught[0].lineno) == (__file__, access_line)
        with pytest.warns(DeprecationWarning, match=f"^{re.escape(message)}$") as caught:
            access_line = sys._getframe().f_lineno + 1
            assert client.order_including_closed is resource
        assert len(caught) == 1
        assert (caught[0].filename, caught[0].lineno) == (__file__, access_line)

    _with_client(async_client, check)
