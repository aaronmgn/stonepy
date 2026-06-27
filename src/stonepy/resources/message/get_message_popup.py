"""Resource method: GetMessagePopup."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import message as _ep
from stonepy.models import GetMessagePopupResponseDTO


class _GetMessagePopupMixin(BaseResource):
    async def get_message_popup(
        self, language: str, client_account_id: int
    ) -> GetMessagePopupResponseDTO:
        """Request to retrieve any popup messages for the given client account."""
        return await _ep.aget_message_popup(self._ctx, language, client_account_id)
