"""Resource method: SavePriceAlert v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import price_alert as _ep
from stonepy.models import SaveAlertRequestDTOv2, SaveAlertResponseDTOv2


class _SavePriceAlertMixin(BaseResource):
    async def save_price_alert(self, request: SaveAlertRequestDTOv2) -> SaveAlertResponseDTOv2:
        """
        Perform a save operation for a client defined price alert. This service call is
        also used to update an alert by saving the new parameters and overwriting the
        previous settings on the same alert.
        """
        return await _ep.asave_price_alert(self._ctx, request)
