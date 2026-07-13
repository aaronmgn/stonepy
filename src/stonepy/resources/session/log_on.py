"""Resource method: LogOn v2. Hand-authored template for the fan-out."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._core.session import require_session_token
from stonepy._endpoints import session as _ep
from stonepy.models import ApiLogOnRequestDTO, ApiLogOnResponseDTOv2


class _LogOnMixin(BaseResource):
    async def log_on(self, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:
        """Create a new session."""
        response = await _ep.alog_on(self._ctx, request)
        token = require_session_token(response.session)
        await self._ctx.session.aset_token(token, request.user_name)

        # Install the refresh callable only after a successful logon, so a failed manual
        # logon cannot clobber a working config-credential refresh.
        async def alogon() -> tuple[str, str]:
            replay = await _ep.alog_on(self._ctx, request)
            return require_session_token(replay.session), request.user_name

        self._ctx.alogon = alogon
        return response
