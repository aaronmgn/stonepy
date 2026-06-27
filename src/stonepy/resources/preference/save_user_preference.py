"""Resource method: SaveUserPreference v2."""

from __future__ import annotations

from stonepy._core.models import ResponseModel
from stonepy._core.resource import BaseResource
from stonepy._endpoints import preference as _ep
from stonepy.models import ApiSavePreferencesRequestDTO


class _SaveUserPreferenceMixin(BaseResource):
    async def save_user_preference(self, request: ApiSavePreferencesRequestDTO) -> ResponseModel:
        """Saves changes to the user's preferences."""
        return await _ep.asave_user_preference(self._ctx, request)
