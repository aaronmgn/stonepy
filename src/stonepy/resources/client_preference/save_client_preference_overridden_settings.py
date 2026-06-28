"""Resource method: SaveClientPreferenceOverriddenSettings v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import client_preference as _ep
from stonepy.models import (
    ApiClientPreferencesOverriddenSettingsSaveRequestDTO,
    ApiClientPreferencesOverriddenSettingsSaveResponseDTO,
)


class _SaveClientPreferenceOverriddenSettingsMixin(BaseResource):
    async def save_client_preference_overridden_settings(
        self, request: ApiClientPreferencesOverriddenSettingsSaveRequestDTO
    ) -> ApiClientPreferencesOverriddenSettingsSaveResponseDTO:
        """Saves the client's preference overridden settings."""
        return await _ep.asave_client_preference_overridden_settings(self._ctx, request)
