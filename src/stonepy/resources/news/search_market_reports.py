"""Resource method: SearchMarketReports."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import NewsResponseDTO


class _SearchMarketReportsMixin(BaseResource):
    async def search_market_reports(
        self,
        market_id: int,
        culture_id: int,
        search_by_headline: bool,
        search_by_body: bool,
        query: str,
        *,
        max_results: int | None = 25,
    ) -> NewsResponseDTO:
        """Search news for the specified market by headline and/or body."""
        return await _ep.asearch_market_reports(
            self._ctx,
            market_id,
            culture_id,
            search_by_headline,
            search_by_body,
            query,
            max_results=max_results,
        )
