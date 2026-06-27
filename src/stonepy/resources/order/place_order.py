"""Resource method: PlaceOrder."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiTradeOrderResponseDTO, NewStopLimitOrderRequestDTO


class _PlaceOrderMixin(BaseResource):
    async def place_order(self, request: NewStopLimitOrderRequestDTO) -> ApiTradeOrderResponseDTO:
        """
        Place a new resting entry order on a particular market. The original generated
        `order()` method remains available for compatibility.
        """
        return await _ep.aorder(self._ctx, request)
