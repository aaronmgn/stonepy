"""Resource method: CancelOrder."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ApiTradeOrderResponseDTO, CancelOrderRequestDTO


class _CancelOrderMixin(BaseResource):
    async def cancel_order(self, request: CancelOrderRequestDTO) -> ApiTradeOrderResponseDTO:
        """
        Cancel the specified order - the order can be a resting entry order or an attached
        closing order to an open position.
        """
        return await _ep.acancel_order(self._ctx, request)
