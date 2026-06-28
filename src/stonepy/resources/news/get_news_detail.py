"""Resource method: GetNewsDetail."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import GetNewsDetailResponseDTO


class _GetNewsDetailMixin(BaseResource):
    async def get_news_detail(self, source: str, story_id: int) -> GetNewsDetailResponseDTO:
        """
        Get the specific market news story matching the news headline ID in the parameter.
        The news headlines and headline IDs are returned from a ListNewsHeadlines call.
        """
        return await _ep.aget_news_detail(self._ctx, source, story_id)
