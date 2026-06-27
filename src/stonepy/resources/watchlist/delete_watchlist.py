"""Resource method: DeleteWatchlist v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import watchlist as _ep
from stonepy.models import DeleteWatchlistResponseDTO


class _DeleteWatchlistMixin(BaseResource):
    async def delete_watchlist(
        self, client_account_id: int, watchlist_id: int
    ) -> DeleteWatchlistResponseDTO:
        """Delete watchlist v2."""
        return await _ep.adelete_watchlist(self._ctx, client_account_id, watchlist_id)
