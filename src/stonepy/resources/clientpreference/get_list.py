"""Resource method: GetList."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import ClientPreferencesRequestDTO, GetClientPreferencesResponseDTO


class _GetListMixin(BaseResource):
    async def get_list(
        self, request: ClientPreferencesRequestDTO
    ) -> GetClientPreferencesResponseDTO:
        """Retrieve a list of client preferences."""
        return await _ep.aget_list(self._ctx, request)
