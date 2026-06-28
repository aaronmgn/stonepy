"""Resource method: ListNewsHeadlinesWithSource."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import ListNewsHeadlinesResponseDTO


class _ListNewsHeadlinesWithSourceMixin(BaseResource):
    async def list_news_headlines_with_source(
        self, source: str, category: str, *, max_results: int | None = 25
    ) -> ListNewsHeadlinesResponseDTO:
        """Get a list of current news headlines for the specified source and category."""
        return await _ep.alist_news_headlines_with_source(
            self._ctx, source, category, max_results=max_results
        )
