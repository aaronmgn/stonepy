"""Resource method: GetPA."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import price_alert as _ep
from stonepy.models import PriceAlertResponseDTO


class _GetPaMixin(BaseResource):
    async def get_pa(
        self, client_account_id: int, *, alert_id: int | None = None
    ) -> PriceAlertResponseDTO:
        """
        Perform a retrieve operation for the specified client price alert, or where no
        parameter is supplied for all price alerts on this client account.
        """
        return await _ep.aget_pa(self._ctx, client_account_id, alert_id=alert_id)
