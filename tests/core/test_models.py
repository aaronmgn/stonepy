from decimal import Decimal

import pytest
from pydantic import Field, ValidationError

from stonepy._core.models import PassthroughResponseModel, RequestModel, ResponseModel


class _Req(RequestModel):
    market_id: int = Field(alias="MarketId")
    quantity: Decimal | None = Field(default=None, alias="Quantity")


class _Resp(ResponseModel):
    order_id: int = Field(alias="OrderId")


def test_request_dumps_by_alias_and_excludes_unset() -> None:
    r = _Req(market_id=7)  # type: ignore[call-arg]
    assert r.model_dump(by_alias=True, exclude_unset=True) == {"MarketId": 7}


def test_request_accepts_python_name_and_alias() -> None:
    assert _Req(market_id=7).market_id == 7  # type: ignore[call-arg]
    assert _Req(MarketId=7).market_id == 7


def test_request_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        _Req(MarketId=7, Bogus=1)  # type: ignore[call-arg]


def test_response_ignores_unknown_fields() -> None:
    resp = _Resp.model_validate({"OrderId": 5, "FutureField": "x"})
    assert resp.order_id == 5


def test_passthrough_response_preserves_unknown_fields() -> None:
    resp = PassthroughResponseModel.model_validate({"Headline": "x", "StoryId": 10})

    assert resp.model_extra == {"Headline": "x", "StoryId": 10}
    assert resp.model_dump(by_alias=True) == {"Headline": "x", "StoryId": 10}


def test_stonex_datetime_reexported_from_models() -> None:
    from stonepy._core.models import StoneXDateTime

    assert StoneXDateTime is not None
