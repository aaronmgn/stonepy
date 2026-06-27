"""Resource method: ListMarketSearchPaginated."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import market as _ep
from stonepy.models import ListMarketSearchPaginatedResponseDTO


class _ListMarketSearchPaginatedMixin(BaseResource):
    async def list_market_search_paginated(
        self,
        query: str,
        search_by_market_code: bool,
        search_by_market_name: bool,
        spread_product_type: bool,
        cfd_product_type: bool,
        binary_product_type: bool,
        ascending_order: bool,
        include_options: bool,
        client_account_id: int,
        *,
        page: int | None = 0,
        page_size: int | None = 10,
        order_by: str | None = "Name",
        use_mobile_short_name: bool | None = False,
        trading_account_id: int | None = None,
    ) -> ListMarketSearchPaginatedResponseDTO:
        """
        Returns a markets page containing a list of markets that meet the search criteria.
        The search can be performed by market code and/or market name, and can include
        CFDs and Spread Bet markets. This method differs from ListMarketSearch in that the
        returned results are paginated.
        """
        return await _ep.alist_market_search_paginated(
            self._ctx,
            query,
            search_by_market_code,
            search_by_market_name,
            spread_product_type,
            cfd_product_type,
            binary_product_type,
            ascending_order,
            include_options,
            client_account_id,
            page=page,
            page_size=page_size,
            order_by=order_by,
            use_mobile_short_name=use_mobile_short_name,
            trading_account_id=trading_account_id,
        )
