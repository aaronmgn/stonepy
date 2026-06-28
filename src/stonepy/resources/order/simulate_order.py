"""Resource method: SimulateOrder."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiSimulateTradeOrderResponseDTO, NewStopLimitOrderRequestDTO


class _SimulateOrderMixin(BaseResource):
    async def simulate_order(
        self, request: NewStopLimitOrderRequestDTO
    ) -> ApiSimulateTradeOrderResponseDTO:
        """
        API call that places a simulated order. Use this service in a margin calculator to
        check how much margin is required to place the order before the order is actually
        placed in an account.
        """
        return await _ep.asimulate_order(self._ctx, request)
