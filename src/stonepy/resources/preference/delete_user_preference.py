"""Resource method: DeleteUserPreference v2."""

from __future__ import annotations

from stonepy._core.models import ResponseModel
from stonepy._core.resource import BaseResource
from stonepy._endpoints import preference as _ep


class _DeleteUserPreferenceMixin(BaseResource):
    async def delete_user_preference(
        self, *, preferences: list[str] | None = None
    ) -> ResponseModel:
        """Deletes user preferences."""
        return await _ep.adelete_user_preference(self._ctx, preferences=preferences)
