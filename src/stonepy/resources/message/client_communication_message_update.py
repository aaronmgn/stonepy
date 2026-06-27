"""Resource method: ClientCommunicationMessageUpdate."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import message as _ep
from stonepy.models import (
    ApiClientCommunicationUpdateRequestDTO,
    ApiClientCommunicationUpdateResponseDTO,
)


class _ClientCommunicationMessageUpdateMixin(BaseResource):
    async def client_communication_message_update(
        self, request: ApiClientCommunicationUpdateRequestDTO
    ) -> ApiClientCommunicationUpdateResponseDTO:
        """
        Request for responses from clients regarding the specified communication message.
        An example call: doPost('/message/ClientCommunicationMessageResponse',
        {"ClientCommunicationId" : 1, "Accepted" : true, "OtherResponse" : "Message"})
        """
        return await _ep.aclient_communication_message_update(self._ctx, request)
