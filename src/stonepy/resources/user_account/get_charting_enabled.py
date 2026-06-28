"""Resource method: GetChartingEnabled."""

from __future__ import annotations

from stonepy._core.models import ResponseModel
from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep


class _GetChartingEnabledMixin(BaseResource):
    async def get_charting_enabled(self, id: str) -> ResponseModel:
        """Checks whether the supplied user account is allowed to see charting data."""
        return await _ep.aget_charting_enabled(self._ctx, id)
