from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import Callable

import pytest

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient

_ALIASES = [
    ("clientapplication", "client_application"),
    ("fixedmargin", "fixed_margin"),
    ("tradingadvisor", "trading_advisor"),
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
