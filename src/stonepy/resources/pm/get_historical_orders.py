"""Resource method: GetHistoricalOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import HistoricalOrdersResponseDTO


class _GetHistoricalOrdersMixin(BaseResource):
    async def get_historical_orders(
        self,
    ) -> HistoricalOrdersResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Retrieves a list of historical limit and market orders over the
        specified time period, which are cancelled, rejected, suspended, closed, or red
        carded together with their associated signal information.
        """
        return await _ep.aget_historical_orders(self._ctx)
