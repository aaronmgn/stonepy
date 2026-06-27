"""Resource method: GetClientAndTradingAccount v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep
from stonepy.models import AccountInformationResponseDTOv2


class _GetClientAndTradingAccountMixin(BaseResource):
    async def get_client_and_trading_account(
        self,
    ) -> AccountInformationResponseDTOv2:
        """
        Returns the User's ClientAccountId and a list of their TradingAccounts. There are
        no parameters for this call.
        """
        return await _ep.aget_client_and_trading_account(self._ctx)
