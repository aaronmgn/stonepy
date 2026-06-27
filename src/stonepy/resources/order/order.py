"""Resource method: Order."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiTradeOrderResponseDTO, NewStopLimitOrderRequestDTO


class _OrderMixin(BaseResource):
    async def order(self, request: NewStopLimitOrderRequestDTO) -> ApiTradeOrderResponseDTO:
        """
        This service is used to place a new resting entry order on a particular market. Do
        not set any order ID fields when requesting a new order, the platform will
        generate them. Note: NFA regulated client accounts cannot place attached If/Done
        stop or limit orders to an entry order.
        """
        return await _ep.aorder(self._ctx, request)
