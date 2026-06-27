"""Resource method: DeleteSession."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import session as _ep
from stonepy.models import ApiLogOffResponseDTO


class _DeleteSessionMixin(BaseResource):
    async def delete_session(self, user_name: str, session: str) -> ApiLogOffResponseDTO:
        """Delete a session. This is how you "log off" from the StoneX API."""
        return await _ep.adelete_session(self._ctx, user_name, session)
