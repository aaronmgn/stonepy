"""Resource method: SaveOverriddenSettings."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import (
    ApiClientPreferencesOverridenSettingsSaveRequestDTO,
    ApiClientPreferencesOverridenSettingsSaveResponseDTO,
)


class _SaveOverriddenSettingsMixin(BaseResource):
    async def save_overridden_settings(
        self, request: ApiClientPreferencesOverridenSettingsSaveRequestDTO
    ) -> ApiClientPreferencesOverridenSettingsSaveResponseDTO:
        """Save client preferences key/value pairs that override default values."""
        return await _ep.asave_overridden_settings(self._ctx, request)
