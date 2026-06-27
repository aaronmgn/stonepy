"""Resource method: Get."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import ClientPreferenceRequestDTO, GetClientPreferenceResponseDTO


class _GetMixin(BaseResource):
    async def get(self, request: ClientPreferenceRequestDTO) -> GetClientPreferenceResponseDTO:
        """
        Retrieve the specified client preference key/value pair. Client preference
        key/value pairs store elements of a trading platform saved by users, for example:
        "Chart_Colour_Schemes".
        """
        return await _ep.aget(self._ctx, request)
