"""Resource method: ListManagedClientAccountsMargin v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import margin as _ep
from stonepy.models import ApiManagedClientAccountsMarginResponseDTO


class _ListManagedClientAccountsMarginMixin(BaseResource):
    async def list_managed_client_accounts_margin(
        self,
    ) -> ApiManagedClientAccountsMarginResponseDTO:
        """
        Retrieves the current margin levels for each managed client assigned to a Trading
        Advisor.
        """
        return await _ep.alist_managed_client_accounts_margin(self._ctx)
