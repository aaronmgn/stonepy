"""Resource method: GetSecureMessages v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import message as _ep
from stonepy.models import SecureMessageCount


class _GetSecureMessagesMixin(BaseResource):
    async def get_secure_messages(
        self, legal_party_id: int, client_account_id: str
    ) -> SecureMessageCount:
        """Returns the information about client's communication secure messages."""
        return await _ep.aget_secure_messages(self._ctx, legal_party_id, client_account_id)
