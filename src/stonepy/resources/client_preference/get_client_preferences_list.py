"""Resource method: GetClientPreferencesList v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import ApiGetClientPreferencesResponseDTO


class _GetClientPreferencesListMixin(BaseResource):
    async def get_client_preferences_list(
        self, keys: list[str], client_account_id: int, string: str
    ) -> ApiGetClientPreferencesResponseDTO:
        """Returns the list of client's preferences."""
        return await _ep.aget_client_preferences_list(self._ctx, keys, client_account_id, string)
