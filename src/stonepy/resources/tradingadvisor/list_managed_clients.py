"""Resource method: ListManagedClients."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import tradingadvisor as _ep
from stonepy.models import ListManagedClientsResponseDTO


class _ListManagedClientsMixin(BaseResource):
    async def list_managed_clients(self, trading_account_id: int) -> ListManagedClientsResponseDTO:
        """List the clients managed by a Trading Advisor."""
        return await _ep.alist_managed_clients(self._ctx, trading_account_id)
