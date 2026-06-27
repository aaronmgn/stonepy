"""Resource method: GetMarketSpread v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import MarketSpreadData


class _GetMarketSpreadMixin(BaseResource):
    async def get_market_spread(self, client_account_id: str, market_id: str) -> MarketSpreadData:
        """Gets a market spread for the specified market."""
        return await _ep.aget_market_spread(self._ctx, client_account_id, market_id)
