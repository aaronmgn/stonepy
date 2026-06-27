"""Resource method: SaveProductInformation v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import ListProductInformationDTO, ListProductInformationResponseDTO


class _SaveProductInformationMixin(BaseResource):
    async def save_product_information(
        self, request: ListProductInformationDTO
    ) -> ListProductInformationResponseDTO:
        """Save Product Information v2 for the specified list of markets."""
        return await _ep.asave_product_information(self._ctx, request)
