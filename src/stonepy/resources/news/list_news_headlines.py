"""Resource method: ListNewsHeadlines."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import ListNewsHeadlinesRequestDTO, ListNewsHeadlinesResponseDTO


class _ListNewsHeadlinesMixin(BaseResource):
    async def list_news_headlines(
        self, request: ListNewsHeadlinesRequestDTO
    ) -> ListNewsHeadlinesResponseDTO:
        """
        Get a list of current news headlines matching the request parameters. The list of
        news headlines can be filtered by various criteria such as market, or geographic
        region.
        """
        return await _ep.alist_news_headlines(self._ctx, request)
