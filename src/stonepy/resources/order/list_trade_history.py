"""Resource method: ListTradeHistory."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import ListTradeHistoryResponseDTO


class _ListTradeHistoryMixin(BaseResource):
    async def list_trade_history(
        self,
        *,
        trading_account_id: int | None = None,
        max_results: int | None = None,
        from_: int | None = None,
    ) -> ListTradeHistoryResponseDTO:
        """
        Queries the trade history for a specified trading account. The result set will
        contain orders with a status of (3 - Open, 9 - Closed) , and includes orders that
        were a trade / stop / limit order . There's currently no corresponding
        GetTradeHistory (as with ListOpenPositions ) .
        """
        return await _ep.alist_trade_history(
            self._ctx,
            trading_account_id=trading_account_id,
            max_results=max_results,
            from_=from_,
        )
