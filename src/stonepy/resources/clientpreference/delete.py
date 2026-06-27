"""Resource method: Delete."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import ClientPreferenceRequestDTO, UpdateDeleteClientPreferenceResponseDTO


class _DeleteMixin(BaseResource):
    async def delete(
        self, request: ClientPreferenceRequestDTO
    ) -> UpdateDeleteClientPreferenceResponseDTO:
        """
        Delete a client preference key/value pair. Client preference key/value pairs store
        elements of a trading platform saved by users, for example:
        "Chart_Colour_Schemes".
        """
        return await _ep.adelete(self._ctx, request)
