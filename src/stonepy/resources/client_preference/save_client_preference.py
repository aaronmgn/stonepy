"""Resource method: SaveClientPreference v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import (
    ApiSaveClientPreferenceRequestDTO,
    ApiUpdateDeleteClientPreferenceResponseDTO,
)


class _SaveClientPreferenceMixin(BaseResource):
    async def save_client_preference(
        self, request: ApiSaveClientPreferenceRequestDTO
    ) -> ApiUpdateDeleteClientPreferenceResponseDTO:
        """Saves changes to the client's preferences."""
        return await _ep.asave_client_preference(self._ctx, request)
