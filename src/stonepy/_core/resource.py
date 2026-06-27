"""Base class for all resource groups. The public _core ABI plugins depend on."""

from __future__ import annotations

from stonepy._core.pipeline import CallContext

ABI_VERSION: int = 1


class BaseResource:
    def __init__(self, ctx: CallContext) -> None:
        self._ctx = ctx
