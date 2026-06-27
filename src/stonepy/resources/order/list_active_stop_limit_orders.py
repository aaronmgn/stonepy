"""Resource method: ListActiveStopLimitOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ListActiveStopLimitOrderResponseDTO


class _ListActiveStopLimitOrdersMixin(BaseResource):
    async def list_active_stop_limit_orders(
        self, *, trading_account_id: int | None = None
    ) -> ListActiveStopLimitOrderResponseDTO:
        """
        Queries for a specified trading account's active stop / limit orders. This URI is
        intended to support a grid in a UI. One usage pattern is to subscribe to streaming
        orders, call this for the initial data to display in the grid, then call the HTTP
        service when you get updates on the order stream to get the updated data in this
        format.
        """
        return await _ep.alist_active_stop_limit_orders(
            self._ctx, trading_account_id=trading_account_id
        )
