"""Resource method: SimulateUpdateOrder."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiSimulateTradeOrderResponseDTO, UpdateStopLimitOrderRequestDTO


class _SimulateUpdateOrderMixin(BaseResource):
    async def simulate_update_order(
        self, request: UpdateStopLimitOrderRequestDTO
    ) -> ApiSimulateTradeOrderResponseDTO:
        """
        Update the details of a simulated resting entry order. For example: change the
        trigger price level or quantity, attach conditional if/done stop/limit orders, or
        attach an OCO relationship.
        """
        return await _ep.asimulate_update_order(self._ctx, request)
