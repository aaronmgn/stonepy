"""Resource method: SimulateCancelOrder."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiSimulateTradeOrderResponseDTO, CancelOrderRequestDTO


class _SimulateCancelOrderMixin(BaseResource):
    async def simulate_cancel_order(
        self, request: CancelOrderRequestDTO
    ) -> ApiSimulateTradeOrderResponseDTO:
        """
        Cancel the specified simulated order - the simulated order can be a resting entry
        order or an attached closing order to an open position.
        """
        return await _ep.asimulate_cancel_order(self._ctx, request)
