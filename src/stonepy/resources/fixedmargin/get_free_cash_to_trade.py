"""Resource method: GetFreeCashToTrade."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import fixedmargin as _ep
from stonepy.models import ApiFreeCashToTradeResponseDTO


class _GetFreeCashToTradeMixin(BaseResource):
    async def get_free_cash_to_trade(
        self,
    ) -> ApiFreeCashToTradeResponseDTO:
        """
        Retrieves the amount of free cash available in the client account that can be used
        to trade.
        """
        return await _ep.aget_free_cash_to_trade(self._ctx)
