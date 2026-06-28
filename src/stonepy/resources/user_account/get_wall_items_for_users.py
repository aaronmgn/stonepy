"""Resource method: GetWallItemsForUsers."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep
from stonepy.models import ApiGetWallItemsForUsersResponseDTO


class _GetWallItemsForUsersMixin(BaseResource):
    async def get_wall_items_for_users(
        self,
    ) -> ApiGetWallItemsForUsersResponseDTO:
        """
        Fetches the wall items for the specified screen names. (Service call used by the
        CI Connect social trading platform.) Note: this requires that the respective CI
        Connect user record in the CI Connect database exists.
        """
        return await _ep.aget_wall_items_for_users(self._ctx)
