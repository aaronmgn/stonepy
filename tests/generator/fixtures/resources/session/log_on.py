from __future__ import annotations

from typing import cast

from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.models import ResponseModel
from stonepy._core.resource import BaseResource


class _LogOnMixin(BaseResource):
    async def log_on(self) -> str:
        return cast(str, await self._ctx.ainvoke(_LOG_ON_SPEC))


_LOG_ON_SPEC = EndpointSpec(
    name="FixtureLogOn",
    method="POST",
    path="/session",
    idempotent=False,
    auth_policy=AuthPolicy.NONE,
    rate_limit_bucket="session",
    response_model=ResponseModel,
)
