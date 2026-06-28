"""Resource method: SimulateUpdateTrade."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiSimulateTradeOrderResponseDTO, UpdateTradeOrderRequestDTO


class _SimulateUpdateTradeMixin(BaseResource):
    async def simulate_update_trade(
        self, request: UpdateTradeOrderRequestDTO
    ) -> ApiSimulateTradeOrderResponseDTO:
        """
        This service is used to simulate updating a trade. For example, simulate adding a
        stop/limit or modifying the details for existing attached orders.
        """
        return await _ep.asimulate_update_trade(self._ctx, request)
