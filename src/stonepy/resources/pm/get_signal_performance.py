"""Resource method: GetSignalPerformance."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import SignalPerformanceResponseDTO


class _GetSignalPerformanceMixin(BaseResource):
    async def get_signal_performance(
        self,
    ) -> SignalPerformanceResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Returns a list of the X top and bottom performing signals as well as a
        win/loss ratio for signals that have expired in the given time period (hours) . A
        percentage format is used to calculate the top and bottom performers.
        """
        return await _ep.aget_signal_performance(self._ctx)
