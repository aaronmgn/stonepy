"""Resource method: GetPriceBarsBeforeDate."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import GetPriceBarResponseDTO


class _GetPriceBarsBeforeDateMixin(BaseResource):
    async def get_price_bars_before_date(
        self,
        market_id: str,
        interval: str,
        span: int,
        to_timestamp_utc: int,
        price_type: str,
        *,
        max_results: int | None = None,
    ) -> GetPriceBarResponseDTO:
        """
        Get historic price bars for the specified market in OHLC (open, high, low, close)
        format, suitable for plotting in candlestick charts. Returns price bars in
        ascending order from before the user given toTimestampUTC . When there are no
        prices for a particular time period, no price bar is returned. Thus, it can appear
        that the array of price bars has "gaps", i.e. the gap between the date & time of
        each price bar might not be equal to interval x span. Sample Urls:
        /market/1234/barhistorybefore?interval=MINUTE&span=15&toTimestampUTC=1400770798 /m
        arket/735/barhistorybefore?interval=HOUR&span=1&toTimestampUTC=1400770798&maxResul
        ts=10 /market/1577/barhistorybefore?interval=DAY&span=1&toTimestampUTC=1400770798
        """
        return await _ep.aget_price_bars_before_date(
            self._ctx,
            market_id,
            interval,
            span,
            to_timestamp_utc,
            price_type,
            max_results=max_results,
        )
