"""Resource method: ListSpreadMarkets."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import spread as _ep
from stonepy.models import ListSpreadMarketsResponseDTO


class _ListSpreadMarketsMixin(BaseResource):
    async def list_spread_markets(
        self,
        client_account_id: int,
        include_options: bool,
        *,
        search_by_market_name: str | None = None,
        search_by_market_code: str | None = None,
        max_results: int | None = 20,
        use_mobile_short_name: bool | None = False,
        trading_account_id: int | None = None,
    ) -> ListSpreadMarketsResponseDTO:
        """
        Returns a list of Spread Betting markets filtered by market name and/or market
        code. Leave the market name and code parameters empty to return all markets
        available to the user.
        """
        return await _ep.alist_spread_markets(
            self._ctx,
            client_account_id,
            include_options,
            search_by_market_name=search_by_market_name,
            search_by_market_code=search_by_market_code,
            max_results=max_results,
            use_mobile_short_name=use_mobile_short_name,
            trading_account_id=trading_account_id,
        )
