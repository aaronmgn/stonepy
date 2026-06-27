"""Resource method: GetNews."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import NewsResponseDTO


class _GetNewsMixin(BaseResource):
    async def get_news(
        self, region: str, culture_id: int, *, max_results: int | None = 25
    ) -> NewsResponseDTO:
        """Get a list of current News stories for the specified region."""
        return await _ep.aget_news(self._ctx, region, culture_id, max_results=max_results)
