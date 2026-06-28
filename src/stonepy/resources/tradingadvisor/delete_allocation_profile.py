"""Resource method: DeleteAllocationProfile."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import tradingadvisor as _ep
from stonepy.models import DeleteAllocationProfileRequestDTO, DeleteAllocationProfileResponseDTO


class _DeleteAllocationProfileMixin(BaseResource):
    async def delete_allocation_profile(
        self, request: DeleteAllocationProfileRequestDTO
    ) -> DeleteAllocationProfileResponseDTO:
        """Delete a Trading Advisor allocation profile."""
        return await _ep.adelete_allocation_profile(self._ctx, request)
