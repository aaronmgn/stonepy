"""Resource method: GetVersionInformation."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import clientapplication as _ep
from stonepy.models import GetVersionInformationResponseDTO


class _GetVersionInformationMixin(BaseResource):
    async def get_version_information(
        self, app_key: str, account_operator_id: int
    ) -> GetVersionInformationResponseDTO:
        """
        Gets version information for a specific client application and (optionally)
        account operator.
        """
        return await _ep.aget_version_information(self._ctx, app_key, account_operator_id)
