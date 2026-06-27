"""Resource method: GetWatchlistsList v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import watchlist as _ep
from stonepy.models import ListWatchlistResponseDTO


class _GetWatchlistsListMixin(BaseResource):
    async def get_watchlists_list(
        self,
        client_account_id: int,
        ids: list[int],
        *,
        include_items: bool | None = None,
        include_market_information: bool | None = None,
    ) -> ListWatchlistResponseDTO:
        """Returns the client's list of watchlists."""
        return await _ep.aget_watchlists_list(
            self._ctx,
            client_account_id,
            ids,
            include_items=include_items,
            include_market_information=include_market_information,
        )
