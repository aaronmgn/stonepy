"""Resource method: GetClientPreferenceOverriddenSettings v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import ApiClientPreferencesOverriddenSettingsGetResponseDTO


class _GetClientPreferenceOverriddenSettingsMixin(BaseResource):
    async def get_client_preference_overridden_settings(
        self, client_account_id: int
    ) -> ApiClientPreferencesOverriddenSettingsGetResponseDTO:
        """Returns the list of client's overridden settings."""
        return await _ep.aget_client_preference_overridden_settings(self._ctx, client_account_id)
