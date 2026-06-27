"""Resource method: SaveWatchlist v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import watchlist as _ep
from stonepy.models import SaveWatchlistRequestDTO, SaveWatchlistResponseDTO


class _SaveWatchlistMixin(BaseResource):
    async def save_watchlist(self, request: SaveWatchlistRequestDTO) -> SaveWatchlistResponseDTO:
        """Save watchlist v2."""
        return await _ep.asave_watchlist(self._ctx, request)
