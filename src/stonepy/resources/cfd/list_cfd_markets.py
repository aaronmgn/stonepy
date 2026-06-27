"""Resource method: ListCfdMarkets."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import cfd as _ep
from stonepy.models import ListCfdMarketsResponseDTO


class _ListCfdMarketsMixin(BaseResource):
    async def list_cfd_markets(
        self,
        client_account_id: int,
        *,
        market_name: str | None = None,
        market_code: str | None = None,
        max_results: int | None = 20,
        use_mobile_short_name: bool | None = False,
        include_options: bool | None = False,
        trading_account_id: int | None = None,
    ) -> ListCfdMarketsResponseDTO:
        """
        Returns a list of CFD markets filtered by market name and/or market code. Leave
        the market name and code parameters empty to return all markets available to the
        user.
        """
        return await _ep.alist_cfd_markets(
            self._ctx,
            client_account_id,
            market_name=market_name,
            market_code=market_code,
            max_results=max_results,
            use_mobile_short_name=use_mobile_short_name,
            include_options=include_options,
            trading_account_id=trading_account_id,
        )
