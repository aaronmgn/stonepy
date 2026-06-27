"""Resource method: GetOverriddenSettings."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import ApiClientPreferencesOverridenSettingsGetResponseDTO


class _GetOverriddenSettingsMixin(BaseResource):
    async def get_overridden_settings(
        self,
    ) -> ApiClientPreferencesOverridenSettingsGetResponseDTO:
        """
        Retrieve the client preference settings that can be overridden from default
        values.
        """
        return await _ep.aget_overridden_settings(self._ctx)
