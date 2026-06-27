"""Resource method: ListActiveOrders."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ListActiveOrdersRequestDTO, ListActiveOrdersResponseDTO


class _ListActiveOrdersMixin(BaseResource):
    async def list_active_orders(
        self, request_dto: ListActiveOrdersRequestDTO
    ) -> ListActiveOrdersResponseDTO:
        """
        Queries the specified trading account for all active orders. This URI returns the
        set of currently active orders for the current user, or optionally for a specified
        trading account belonging to the current user. Each order in the returned set can
        be either a stop/limit order or a trade. Use the TypeId member on
        ApiActiveOrderDTO to determine whether it is a stop/limit order or a trade.
        """
        return await _ep.alist_active_orders(self._ctx, request_dto)
