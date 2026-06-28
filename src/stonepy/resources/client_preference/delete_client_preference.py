"""Resource method: DeleteClientPreference v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import ApiUpdateDeleteClientPreferenceResponseDTO


class _DeleteClientPreferenceMixin(BaseResource):
    async def delete_client_preference(
        self, client_account_id: int, key: str
    ) -> ApiUpdateDeleteClientPreferenceResponseDTO:
        """Deletes the client's preferences."""
        return await _ep.adelete_client_preference(self._ctx, client_account_id, key)
