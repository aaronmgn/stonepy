"""Resource method: SaveClientCommunicationMessageResponse v2."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import message as _ep
from stonepy.models import (
    ApiClientCommunicationUpdateRequestDTO,
    ApiClientCommunicationUpdateResponseDTO,
)


class _SaveClientCommunicationMessageResponseMixin(BaseResource):
    async def save_client_communication_message_response(
        self, request: ApiClientCommunicationUpdateRequestDTO
    ) -> ApiClientCommunicationUpdateResponseDTO:
        """Saves changes to the client's communication message response."""
        return await _ep.asave_client_communication_message_response(self._ctx, request)
