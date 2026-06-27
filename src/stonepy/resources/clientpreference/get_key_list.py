"""Resource method: GetKeyList."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientpreference as _ep
from stonepy.models import GetKeyListClientPreferenceResponseDTO


class _GetKeyListMixin(BaseResource):
    async def get_key_list(
        self,
    ) -> GetKeyListClientPreferenceResponseDTO:
        """
        Get a list of client preferences key/value pairs. There are no parameters in this
        call. Client preference key/value pairs store elements of a trading platform saved
        by users, for example: "Chart_Colour_Schemes".
        """
        return await _ep.aget_key_list(self._ctx)
