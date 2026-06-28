"""Resource method: ValidateSession v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import session as _ep
from stonepy.models import ApiValidateSessionRequestDTOv2, ApiValidateSessionResponseDTO


class _ValidateSessionMixin(BaseResource):
    async def validate_session(
        self, request: ApiValidateSessionRequestDTOv2
    ) -> ApiValidateSessionResponseDTO:
        """
        Validates a session - checks that your session ID and username combination is
        valid.
        """
        return await _ep.avalidate_session(self._ctx, request)
