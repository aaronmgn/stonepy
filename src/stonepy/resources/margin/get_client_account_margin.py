"""Resource method: GetClientAccountMargin v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import margin as _ep
from stonepy.models import ClientAccountMarginResponseDTO


class _GetClientAccountMarginMixin(BaseResource):
    async def get_client_account_margin(
        self, client_account_id: int
    ) -> ClientAccountMarginResponseDTO:
        """Returns the information about client account margin."""
        return await _ep.aget_client_account_margin(self._ctx, client_account_id)
