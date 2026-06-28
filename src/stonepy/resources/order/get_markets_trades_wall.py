"""Resource method: GetMarketsTradesWall."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import order as _ep
from stonepy.models import GetMarketsTradesWallResponseDTO


class _GetMarketsTradesWallMixin(BaseResource):
    async def get_markets_trades_wall(
        self, market_i_ds: list[int], number_of_results: int
    ) -> GetMarketsTradesWallResponseDTO:
        """
        Gets a list of the latest trading activities performed by the members of the CI
        Connect community on the requested markets. The result consists of all the trade
        actions recorded in the system for the requested markets regardless of user.
        (Service call used by the CI Connect social trading platform.) Note: this requires
        an existence of the respective CI Connect user record in the CI Connect database.
        """
        return await _ep.aget_markets_trades_wall(self._ctx, market_i_ds, number_of_results)
