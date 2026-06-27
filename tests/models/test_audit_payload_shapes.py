from __future__ import annotations

from typing import Any, cast, get_args, get_origin

import pytest
from pydantic import TypeAdapter

from stonepy.models import (
    ApiIfDoneDTOv2,
    ApiManagedTradeDTO,
    ApiOpenPositionDTOv2,
    GetPriceTickResponseDTO,
    ListOpenPositionsResponseDTO,
    NewTradeOrderRequestDTO,
)


def _allows_list(annotation: object) -> bool:
    if get_origin(annotation) is list:
        return True
    return any(get_origin(item) is list for item in get_args(annotation))


@pytest.mark.parametrize(
    ("model_cls", "field_name"),
    [
        (GetPriceTickResponseDTO, "price_ticks"),
        (ListOpenPositionsResponseDTO, "open_positions"),
        (ApiOpenPositionDTOv2, "managed_trades"),
        (NewTradeOrderRequestDTO, "if_done"),
    ],
)
def test_audited_array_fields_are_typed_as_lists(
    model_cls: type[Any],
    field_name: str,
) -> None:
    field = model_cls.model_fields[field_name]

    assert _allows_list(field.annotation)
    if model_cls is NewTradeOrderRequestDTO:
        assert not field.is_required()


def test_price_tick_response_accepts_array_payload() -> None:
    parsed = GetPriceTickResponseDTO.model_validate({"PriceTicks": [{"Price": "1.23"}]})

    assert parsed.price_ticks is not None
    assert len(parsed.price_ticks) == 1
    assert parsed.price_ticks[0].price is not None


def test_nested_array_payloads_parse_as_lists() -> None:
    position = ApiOpenPositionDTOv2.model_validate({"ManagedTrades": [{"OrderId": 123}]})
    request_if_done = cast(
        list[ApiIfDoneDTOv2],
        TypeAdapter(NewTradeOrderRequestDTO.model_fields["if_done"].annotation).validate_python(
            [{"Stop": {"OrderId": 456}, "Limit": {"OrderId": 789}}],
        ),
    )

    assert isinstance(position.managed_trades, list)
    assert isinstance(position.managed_trades[0], ApiManagedTradeDTO)
    assert isinstance(request_if_done, list)
    assert isinstance(request_if_done[0], ApiIfDoneDTOv2)
