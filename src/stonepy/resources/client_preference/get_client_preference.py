"""Resource method: GetClientPreference v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import ApiGetClientPreferenceResponseDTO


class _GetClientPreferenceMixin(BaseResource):
    async def get_client_preference(
        self, client_account_id: int, key: str
    ) -> ApiGetClientPreferenceResponseDTO:
        """Returns the client's preferences."""
        return await _ep.aget_client_preference(self._ctx, client_account_id, key)
