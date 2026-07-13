"""Resource method: DeleteSession."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import session as _ep
from stonepy.models import ApiLogOffResponseDTO


class _DeleteSessionMixin(BaseResource):
    async def delete_session(self, user_name: str, session: str) -> ApiLogOffResponseDTO:
        """Delete a session. This is how you "log off" from the StoneX API."""
        response = await _ep.adelete_session(self._ctx, user_name, session)
        if response.logged_out is not False:
            # Drop the local token so later calls do not send a known-invalid session.
            await self._ctx.session.aclear()
        return response
