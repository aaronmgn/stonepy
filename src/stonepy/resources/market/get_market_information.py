"""Resource method: GetMarketInformation v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import GetMarketInformationResponseDTO


class _GetMarketInformationMixin(BaseResource):
    async def get_market_information(
        self, market_id: str, client_account_id: int
    ) -> GetMarketInformationResponseDTO:
        """Get Market Information for the single specified market supplied in the parameter."""
        return await _ep.aget_market_information(self._ctx, market_id, client_account_id)
