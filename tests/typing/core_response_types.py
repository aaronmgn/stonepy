"""Both checker gates must retain concrete response types across parsing/narrowing."""

from typing import assert_type

import httpx

from stonepy._core.endpoint import EndpointSpec
from stonepy._core.models import ListResponse, ScalarResponse, UnspecifiedResponse
from stonepy._core.pipeline import parse_response
from stonepy._core.status import (
    StatusDecoder,
    default_status_decoder,
    normalize_status_decoder,
)
from stonepy.models import ApiLogOnResponseDTOv2


def response_types(
    response: httpx.Response,
    model: EndpointSpec[ApiLogOnResponseDTOv2],
    array: EndpointSpec[ListResponse[ApiLogOnResponseDTOv2]],
    scalar: EndpointSpec[ScalarResponse[bool]],
    unspecified: EndpointSpec[UnspecifiedResponse],
) -> None:
    assert_type(parse_response(model, response), ApiLogOnResponseDTOv2)
    assert_type(parse_response(array, response), ListResponse[ApiLogOnResponseDTOv2])
    assert_type(parse_response(scalar, response), ScalarResponse[bool])
    assert_type(parse_response(unspecified, response), UnspecifiedResponse)
    decoder = normalize_status_decoder(default_status_decoder)
    assert_type(decoder, StatusDecoder | None)
