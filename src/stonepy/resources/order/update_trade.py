"""Resource method: UpdateTrade."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiTradeOrderResponseDTO, UpdateTradeOrderRequestDTO


class _UpdateTradeMixin(BaseResource):
    async def update_trade(self, request: UpdateTradeOrderRequestDTO) -> ApiTradeOrderResponseDTO:
        """
        This service is used for two functions: Add a new closing stop loss and/or take
        profit limit order attached to an open position. Modify the details for existing
        closing orders attached to an open position.
        """
        return await _ep.aupdate_trade(self._ctx, request)
