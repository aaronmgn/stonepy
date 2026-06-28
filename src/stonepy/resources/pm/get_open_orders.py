"""Resource method: GetOpenOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import pm as _ep
from stonepy.models import OpenOrdersResponseDTO


class _GetOpenOrdersMixin(BaseResource):
    async def get_open_orders(
        self,
    ) -> OpenOrdersResponseDTO:
        """
        All service calls and DTOs related to Predicted Markets are for internal StoneX
        use only. Retrieves a list of market orders that have open status along with their
        associated signal information.
        """
        return await _ep.aget_open_orders(self._ctx)
