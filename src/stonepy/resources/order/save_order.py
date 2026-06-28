"""Resource method: SaveOrder v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ExecutionResponseDTO, ExecutionVenueRequestDTO


class _SaveOrderMixin(BaseResource):
    async def save_order(self, request: ExecutionVenueRequestDTO) -> ExecutionResponseDTO:
        """Creates an order."""
        return await _ep.asave_order(self._ctx, request)
