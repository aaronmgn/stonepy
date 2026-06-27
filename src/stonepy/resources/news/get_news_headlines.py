"""Resource method: GetNewsHeadlines."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy._endpoints.news import NewsHeadlinesResponseDTO


class _GetNewsHeadlinesMixin(BaseResource):
    async def get_news_headlines(
        self, region: str, culture_id: int, *, max_results: int | None = 25
    ) -> NewsHeadlinesResponseDTO:
        """Get a list of current news headlines for the specified region."""
        return await _ep.aget_news_headlines(self._ctx, region, culture_id, max_results=max_results)
