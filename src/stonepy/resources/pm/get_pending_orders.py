"""Resource method: GetPendingOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import PendingOrdersResponseDTO


class _GetPendingOrdersMixin(BaseResource):
    async def get_pending_orders(
        self,
    ) -> PendingOrdersResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Retrieves the list of pending orders.
        """
        return await _ep.aget_pending_orders(self._ctx)
