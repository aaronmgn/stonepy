"""Resource method: SaveSignalPreferences."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import ApiSaveSignalPreferencesResponseDTO


class _SaveSignalPreferencesMixin(BaseResource):
    async def save_signal_preferences(
        self,
    ) -> ApiSaveSignalPreferencesResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Saves the signal preferences for the authenticated user.
        """
        return await _ep.asave_signal_preferences(self._ctx)
