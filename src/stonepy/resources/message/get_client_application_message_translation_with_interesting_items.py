"""Resource method: GetClientApplicationMessageTranslationWithInterestingItems."""

from __future__ import annotations

from stonepy._core.resource import BaseResource
from stonepy._endpoints import message as _ep
from stonepy.models import (
    ApiClientApplicationMessageTranslationRequestDTO,
    ApiClientApplicationMessageTranslationResponseDTO,
)


class _GetClientApplicationMessageTranslationWithInterestingItemsMixin(BaseResource):
    async def get_client_application_message_translation_with_interesting_items(
        self, request: ApiClientApplicationMessageTranslationRequestDTO
    ) -> ApiClientApplicationMessageTranslationResponseDTO:
        """
        Use the message translation service to get client specific translated text strings
        for specific keys.
        """
        return await _ep.aget_client_application_message_translation_with_interesting_items(
            self._ctx, request
        )
