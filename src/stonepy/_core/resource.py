"""Base class for resource groups; the stable ABI that out-of-tree plugins build on."""

from __future__ import annotations

from stonepy._core.pipeline import CallContext

ABI_VERSION: int = 1
"""Version of the resource ABI; bumped when the plugin base contract changes."""


class BaseResource:
    """Base class every resource group (and resource plugin) subclasses.

    Holds the shared [`CallContext`][stonepy._core.pipeline.CallContext] that resource methods
    use to invoke endpoints. Concrete resource groups mix in one method per endpoint.
    """

    def __init__(self, ctx: CallContext) -> None:
        self._ctx = ctx
