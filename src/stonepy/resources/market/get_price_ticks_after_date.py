"""Resource method: GetPriceTicksAfterDate."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import GetPriceTickResponseDTO


class _GetPriceTicksAfterDateMixin(BaseResource):
    async def get_price_ticks_after_date(
        self,
        market_id: str,
        from_time_stamp_utc: int,
        price_type: str,
        *,
        max_results: int | None = None,
    ) -> GetPriceTickResponseDTO:
        """
        Get historic price ticks for the specified market, which by default is the mid
        price. (A price tick occurs at the point in time the pricing engine is updated and
        contains the Ask, Bid and Mid prices at that instant in time.) Returns price ticks
        in ascending order after the user given fromTimestampUTC . The length of time that
        elapses between each tick is usually different.
        """
        return await _ep.aget_price_ticks_after_date(
            self._ctx, market_id, from_time_stamp_utc, price_type, max_results=max_results
        )
