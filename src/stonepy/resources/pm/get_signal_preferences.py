"""Resource method: GetSignalPreferences."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import PreferenceDTO


class _GetSignalPreferencesMixin(BaseResource):
    async def get_signal_preferences(
        self,
    ) -> PreferenceDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Retrieves the signal preferences for the authenticated user.
        """
        return await _ep.aget_signal_preferences(self._ctx)
