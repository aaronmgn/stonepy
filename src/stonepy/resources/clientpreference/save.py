"""Resource method: Save."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import SaveClientPreferenceRequestDTO, UpdateDeleteClientPreferenceResponseDTO


class _SaveMixin(BaseResource):
    async def save(
        self, request: SaveClientPreferenceRequestDTO
    ) -> UpdateDeleteClientPreferenceResponseDTO:
        """
        Perform a save operation for client preferences in key/value pairs. Key/value
        pairs store configuration elements of a trading platform, for example:
        "Chart_Colour_Schemes".
        """
        return await _ep.asave(self._ctx, request)
