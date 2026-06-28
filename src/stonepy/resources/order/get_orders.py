"""Resource method: GetOrders v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import EnrichedOrderDTO


class _GetOrdersMixin(BaseResource):
    async def get_orders(
        self, client_account_id: str, *, limit: int | None = None
    ) -> EnrichedOrderDTO:
        """Query for orders by a specific client account id."""
        return await _ep.aget_orders(self._ctx, client_account_id, limit=limit)
