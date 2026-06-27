"""Resource method: GetStory."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import news as _ep
from stonepy.models import StoryResponseDTO


class _GetStoryMixin(BaseResource):
    async def get_story(self, story_id: int) -> StoryResponseDTO:
        """Get the detail for the specific news story matching the story ID in the parameter."""
        return await _ep.aget_story(self._ctx, story_id)
