"""Resource method: LogOn v2. Hand-authored template for the fan-out."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import session as _ep
from stonepy.models import ApiLogOnRequestDTO, ApiLogOnResponseDTOv2


class _LogOnMixin(BaseResource):
    async def log_on(self, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:
        """Create a new session."""

        async def alogon() -> tuple[str, str]:
            return (await _ep.alog_on(self._ctx, request)).session or "", request.user_name

        self._ctx.alogon = alogon
        response = await _ep.alog_on(self._ctx, request)
        await self._ctx.session.aset_token(response.session or "", request.user_name)
        return response
