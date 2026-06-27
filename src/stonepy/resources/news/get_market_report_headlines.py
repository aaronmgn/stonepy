"""Resource method: GetMarketReportHeadlines."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy._endpoints.news import NewsHeadlinesResponseDTO


class _GetMarketReportHeadlinesMixin(BaseResource):
    async def get_market_report_headlines(
        self, market_id: int, culture_id: int, *, max_results: int | None = 25
    ) -> NewsHeadlinesResponseDTO:
        """Retrieve a list of current news headlines for a specific market."""
        return await _ep.aget_market_report_headlines(
            self._ctx, market_id, culture_id, max_results=max_results
        )
