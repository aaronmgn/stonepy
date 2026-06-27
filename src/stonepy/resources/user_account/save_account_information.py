"""Resource method: SaveAccountInformation v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import user_account as _ep
from stonepy.models import ApiAccountInformationSaveRequestDTO, ApiAccountInformationSaveResponseDTO


class _SaveAccountInformationMixin(BaseResource):
    async def save_account_information(
        self, request: ApiAccountInformationSaveRequestDTO
    ) -> ApiAccountInformationSaveResponseDTO:
        """
        Saves changes to the users account information. Currently only the user email
        address in the account information can be changed and saved.
        """
        return await _ep.asave_account_information(self._ctx, request)
