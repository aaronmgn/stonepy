"""Resource method: GetOrderHistory v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import OrderHistoryDTO


class _GetOrderHistoryMixin(BaseResource):
    async def get_order_history(
        self,
        client_account_id: int,
        *,
        start_date_time: int | None = None,
        end_date_time: int | None = None,
        page_size: int | None = None,
        page: int | None = None,
    ) -> list[OrderHistoryDTO]:
        """Queries for an order history."""
        return await _ep.aget_order_history(
            self._ctx,
            client_account_id,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            page_size=page_size,
            page=page,
        )
