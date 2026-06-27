"""Resource method: GetUserPreference v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import preference as _ep
from stonepy.models import ApiGetPreferencesResponseDTO


class _GetUserPreferenceMixin(BaseResource):
    async def get_user_preference(
        self, *, preferences: list[str] | None = None
    ) -> ApiGetPreferencesResponseDTO:
        """Returns the user's preferences."""
        return await _ep.aget_user_preference(self._ctx, preferences=preferences)
