"""Resource method: GetChangedOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import GetChangedOrdersResponseDTO


class _GetChangedOrdersMixin(BaseResource):
    async def get_changed_orders(
        self, trading_account_id: int, from_: int
    ) -> GetChangedOrdersResponseDTO:
        """
        Queries the specified trading account's order history. Includes all orders changed
        after the given from parameter value. Note: should only be used for the FIX API.
        Can return unexpected results while using with other purposes.
        """
        return await _ep.aget_changed_orders(self._ctx, trading_account_id, from_)
