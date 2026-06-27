"""Resource method: ChangePassword."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import session as _ep
from stonepy.models import ApiChangePasswordRequestDTO, ApiChangePasswordResponseDTO


class _ChangePasswordMixin(BaseResource):
    async def change_password(
        self, request: ApiChangePasswordRequestDTO
    ) -> ApiChangePasswordResponseDTO:
        """Change a user's password."""
        return await _ep.achange_password(self._ctx, request)
