"""Resource method: GetMultipleUsersDetailsByFacebookIds."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep
from stonepy.models import ApiGetMultipleUsersDetailsResponseDTO


class _GetMultipleUsersDetailsByFacebookIdsMixin(BaseResource):
    async def get_multiple_users_details_by_facebook_ids(
        self,
    ) -> ApiGetMultipleUsersDetailsResponseDTO:
        """
        Fetches the CI Connect user details for each of the Facebook IDs that are passed
        in the parameter. (Service call used by the CI Connect social trading platform.)
        Note: this requires that the respective CI Connect user record in the CI Connect
        database exists.
        """
        return await _ep.aget_multiple_users_details_by_facebook_ids(self._ctx)
