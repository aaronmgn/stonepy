"""Resource method: UpdateTradeFM."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import fixedmargin as _ep
from stonepy.models import FixedMarginOrderResponseDTO, UpdateFixedMarginTradeOrderRequestDTO


class _UpdateTradeFmMixin(BaseResource):
    async def update_trade_fm(
        self, request: UpdateFixedMarginTradeOrderRequestDTO
    ) -> FixedMarginOrderResponseDTO:
        """This service is used to update a fixed margin trade."""
        return await _ep.aupdate_trade_fm(self._ctx, request)
