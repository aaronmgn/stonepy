"""Resource method: SaveMarketInformation."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import ApiSaveMarketInformationResponseDTO, SaveMarketInformationRequestDTO


class _SaveMarketInformationMixin(BaseResource):
    async def save_market_information(
        self, request: SaveMarketInformationRequestDTO
    ) -> ApiSaveMarketInformationResponseDTO:
        """
        Save Market Information for the specified list of markets. Currently, this is used
        to store the per market Price Tolerance setting when changed by the user.
        """
        return await _ep.asave_market_information(self._ctx, request)
