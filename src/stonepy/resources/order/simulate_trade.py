"""Resource method: SimulateTrade."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiSimulateTradeOrderResponseDTO, NewTradeOrderRequestDTO


class _SimulateTradeMixin(BaseResource):
    async def simulate_trade(
        self, request: NewTradeOrderRequestDTO
    ) -> ApiSimulateTradeOrderResponseDTO:
        """
        API call that places a simulated trade. Use this service in a margin calculator to
        check how much margin is required to place the trade before the trade is actually
        executed.
        """
        return await _ep.asimulate_trade(self._ctx, request)
