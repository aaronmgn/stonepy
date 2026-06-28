"""Resource method: ListActiveSignals."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import ActiveSignalsResponseDTO


class _ListActiveSignalsMixin(BaseResource):
    async def list_active_signals(
        self,
    ) -> ActiveSignalsResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Returns a list of all active signals. These are signals with a status of
        WithinTriggerLevel (2) or Triggered (3).
        """
        return await _ep.alist_active_signals(self._ctx)
