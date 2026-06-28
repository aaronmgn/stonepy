"""Resource method: Search."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep
from stonepy.models import ApiTraderSearchResponseDTO


class _SearchMixin(BaseResource):
    async def search(self, page_number: int) -> ApiTraderSearchResponseDTO:
        """
        Performs a search of CI Connect users based on the user specified search criteria.
        (Service call used by the CI Connect social trading platform.) Note: this requires
        that the respective CI Connect user record in the CI Connect database exists. Only
        users registered with CI Connect are searched.
        """
        return await _ep.asearch(self._ctx, page_number)
