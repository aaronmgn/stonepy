"""Resource method: LogOn v2. Hand-authored template for the fan-out."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._core.session import require_session_token
from stonepy._endpoints import session as _ep
from stonepy.models import ApiLogOnRequestDTO, ApiLogOnResponseDTOv2


class _LogOnMixin(BaseResource):
    async def log_on(self, request: ApiLogOnRequestDTO) -> ApiLogOnResponseDTOv2:
        """Create a new session."""
        snapshot = ApiLogOnRequestDTO.model_validate(
            request.model_dump(by_alias=True, exclude_unset=True, mode="python")
        )
        response = await _ep.alog_on(self._ctx, snapshot)
        token = require_session_token(response.session)

        async def alogon() -> tuple[str, str]:
            replay = await _ep.alog_on(self._ctx, snapshot)
            return require_session_token(replay.session), snapshot.user_name

        await self._ctx.acommit(token, snapshot.user_name, alogon)
        return response
