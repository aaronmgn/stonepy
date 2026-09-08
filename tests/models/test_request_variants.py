from __future__ import annotations

import asyncio
from typing import ForwardRef, get_args

import pytest
from pydantic import BaseModel, ValidationError

import stonepy.models as models
from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy._core.models import RequestModel, RequestVariantModel, ResponseModel
from stonepy._endpoints.order import TRADE_SPEC

VARIANT_SOURCES = frozenset(
    name.removeprefix("Request") for name in models.__all__ if name.startswith("Request")
)
ROOTS = frozenset(
    name
    for name in models.__all__
    if issubclass(getattr(models, name), RequestModel)
    and not issubclass(getattr(models, name), RequestVariantModel)
)


def _order_payload() -> dict[str, object]:
    return {
        "MarketId": 1,
        "Currency": "USD",
        "AutoRollover": False,
        "Direction": "Buy",
        "Quantity": "1",
        "QuoteId": 1,
        "PositionMethodId": 1,
        "BidPrice": "1",
        "OfferPrice": "2",
        "AuditId": "audit",
        "TradingAccountId": 1,
        "Close": [],
        "Reference": "StoneX API",
        "AllocationProfileId": 1,
        "PriceTolerance": 0,
    }


def _stop_payload() -> dict[str, object]:
    return {
        key: value
        for key, value in _order_payload().items()
        if key not in {"QuoteId", "Close", "PriceTolerance"}
    } | {
        "OrderId": 1,
        "Applicability": "GTC",
        "ExpiryDateTimeUTC": "/Date(1577836800000)/",
        "Guaranteed": False,
        "TriggerPrice": "1",
        "OrderReference": "",
        "Source": "",
    }


def _assert_typo(
    model: type[BaseModel], payload: dict[str, object], loc: tuple[object, ...]
) -> None:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(payload)
    assert any(
        error["type"] == "extra_forbidden" and error["loc"] == loc
        for error in caught.value.errors()
    )


def test_new_trade_if_done_typo_is_rejected() -> None:
    _assert_typo(
        models.NewTradeOrderRequestDTO,
        _order_payload() | {"IfDone": [{"Stpo": {}}]},
        ("IfDone", 0, "Stpo"),
    )


def test_new_stop_limit_if_done_typo_is_rejected() -> None:
    _assert_typo(
        models.NewStopLimitOrderRequestDTO,
        _stop_payload() | {"IfDone": [{"Stpo": {}}]},
        ("IfDone", 0, "Stpo"),
    )
    assert models.NewStopLimitOrderRequestDTO.model_validate(_stop_payload()).oco_order is None


def test_nested_stop_limit_typo_is_rejected() -> None:
    _assert_typo(
        models.NewTradeOrderRequestDTO,
        _order_payload() | {"IfDone": [{"Stop": {"TrigerPrice": "1"}}]},
        ("IfDone", 0, "Stop", "TrigerPrice"),
    )


def test_response_unknown_nested_field_remains_tolerated() -> None:
    order = models.ApiOrderDTOv2.model_validate({"IfDone": [{"Stpo": {}}]})
    response = models.ApiTradeOrderResponseDTO.model_validate(
        {"Orders": [{"IfDone": [{"Stpo": {}}]}]}
    )
    assert order.if_done is not None and order.if_done[0].stop is None
    assert response.orders is not None and response.orders[0].if_done is not None


def test_tolerant_instance_is_rejected_in_request_position() -> None:
    with pytest.raises(ValidationError) as caught:
        models.NewTradeOrderRequestDTO.model_validate(
            _order_payload() | {"IfDone": [models.ApiIfDoneDTOv2()]}
        )
    assert caught.value.errors()[0]["type"] in {"model_type", "value_error"}
    message = (
        "expected a mapping or a RequestApiIfDoneDTOv2 instance; "
        "other model instances are not accepted in request positions"
    )
    assert message in caught.value.errors()[0]["msg"]
    own = models.RequestApiIfDoneDTOv2()
    assert models.RequestApiIfDoneDTOv2.model_validate(own) is own


def test_endpoint_rejects_tolerant_request_instance() -> None:
    with (
        StoneXClient(ClientConfig(base_url="https://example.test")) as client,
        pytest.raises(ValidationError),
    ):
        client._ctx.invoke(TRADE_SPEC, body=models.ApiIfDoneDTOv2())


def test_async_endpoint_rejects_tolerant_request_instance() -> None:
    async def run() -> None:
        async with AsyncStoneXClient(ClientConfig(base_url="https://example.test")) as client:
            with pytest.raises(ValidationError):
                await client._ctx.ainvoke(TRADE_SPEC, body=models.ApiIfDoneDTOv2())

    asyncio.run(run())


@pytest.mark.parametrize("name", sorted(VARIANT_SOURCES))
def test_request_variant_defaults_and_aliases_match_original(name: str) -> None:
    original = getattr(models, name)
    variant = getattr(models, f"Request{name}")
    assert issubclass(original, ResponseModel)
    assert issubclass(variant, RequestVariantModel)
    assert original.__doc__ == variant.__doc__
    assert variant.model_fields.keys() == original.model_fields.keys()
    for key, field in original.model_fields.items():
        twin = variant.model_fields[key]
        assert (twin.alias, twin.default, twin.default_factory, twin.repr, twin.description) == (
            field.alias,
            field.default,
            field.default_factory,
            field.repr,
            field.description,
        )


def _annotation_types(annotation: object) -> set[type[BaseModel]]:
    assert not isinstance(annotation, str | ForwardRef)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return {annotation}
    return set().union(*(_annotation_types(arg) for arg in get_args(annotation)))


def test_request_variants_rebuild_forward_references() -> None:
    for name in VARIANT_SOURCES:
        variant = getattr(models, f"Request{name}")
        variant.model_rebuild(force=True)
        for field in variant.model_fields.values():
            _annotation_types(field.annotation)


def test_request_typed_endpoint_params_use_variants() -> None:
    annotation = models.SaveWatchlistRequestDTO.model_fields["watchlist"].annotation
    assert models.RequestApiClientAccountWatchlistDTO in _annotation_types(annotation)


def test_every_request_reachable_model_forbids_extra() -> None:
    pending = [getattr(models, name) for name in ROOTS]
    visited = set()
    while pending:
        model = pending.pop()
        if model in visited:
            continue
        visited.add(model)
        assert issubclass(model, RequestModel)
        assert model.model_config["extra"] == "forbid"
        for field in model.model_fields.values():
            pending.extend(_annotation_types(field.annotation) - visited)
    assert len(visited) == 55
    assert len(VARIANT_SOURCES) == 25
    assert len(ROOTS) == 30


def test_request_variant_keys_are_exact_alias_or_python_name() -> None:
    with pytest.raises(ValidationError) as caught:
        models.RequestApiStopLimitOrderDTOv2.model_validate({"triggerPrice": "1"})
    assert caught.value.errors()[0]["type"] == "extra_forbidden"
    assert models.ApiStopLimitOrderDTOv2.model_validate({"triggerPrice": "1"}).trigger_price == 1
    for key in ("TriggerPrice", "trigger_price"):
        assert models.RequestApiStopLimitOrderDTOv2.model_validate({key: "1"}).trigger_price == 1
