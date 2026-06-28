"""Resource method: GetClientPreferencesKeyList v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import ApiGetKeyListClientPreferenceResponseDTO


class _GetClientPreferencesKeyListMixin(BaseResource):
    async def get_client_preferences_key_list(
        self, client_account_id: int
    ) -> ApiGetKeyListClientPreferenceResponseDTO:
        """Returns the list of keys for client's preferences."""
        return await _ep.aget_client_preferences_key_list(self._ctx, client_account_id)
