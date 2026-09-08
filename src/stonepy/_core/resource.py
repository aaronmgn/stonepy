"""Base class for built-in and explicitly constructed resource groups."""

from __future__ import annotations

from stonepy._core.pipeline import CallContext


class BaseResource:
    """Base class for resource groups.

    Holds the shared [`CallContext`][stonepy._core.pipeline.CallContext] that resource methods
    use to invoke endpoints. Concrete resource groups mix in one method per endpoint.

    Args:
        ctx: Call state owned by the caller. The caller manages its transport lifetime.
    """

    def __init__(self, ctx: CallContext) -> None:
        self._ctx = ctx

    @property
    def call_context(self) -> CallContext:
        """Return the shared call state used to invoke endpoints.

        This property cannot be reassigned; its context contains mutable state.
        """
        return self._ctx
