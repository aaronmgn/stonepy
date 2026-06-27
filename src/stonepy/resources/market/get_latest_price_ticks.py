"""Resource method: GetLatestPriceTicks."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import GetPriceTickResponseDTO


class _GetLatestPriceTicksMixin(BaseResource):
    async def get_latest_price_ticks(
        self, market_id: str, price_ticks: int, price_type: str
    ) -> GetPriceTickResponseDTO:
        """
        Get historic price ticks for the specified market, which by default is the mid
        price. (A price tick occurs at the point in time the pricing engine is updated and
        contains the Ask, Bid and Mid prices at that instant in time.) Returns price ticks
        in ascending order up to the current time. The length of time that elapses between
        each tick is usually different.
        """
        return await _ep.aget_latest_price_ticks(self._ctx, market_id, price_ticks, price_type)
