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


def test_response_matches_keys_case_insensitively() -> None:
    # CIAPI v2 returns camelCase while the models alias PascalCase; all three forms must populate.
    assert _Resp.model_validate({"OrderId": 1}).order_id == 1
    assert _Resp.model_validate({"orderId": 2}).order_id == 2
    assert _Resp.model_validate({"order_id": 3}).order_id == 3


def test_response_case_insensitive_match_is_recursive() -> None:
    class _Nested(ResponseModel):
        inner: _Resp | None = Field(default=None, alias="Inner")

    parsed = _Nested.model_validate({"inner": {"orderId": 9}})
    assert parsed.inner is not None
    assert parsed.inner.order_id == 9


def test_passthrough_response_preserves_unknown_fields() -> None:
    resp = PassthroughResponseModel.model_validate({"Headline": "x", "StoryId": 10})

    assert resp.model_extra == {"Headline": "x", "StoryId": 10}
    assert resp.model_dump(by_alias=True) == {"Headline": "x", "StoryId": 10}


def test_stonex_datetime_reexported_from_models() -> None:
    from stonepy._core.models import StoneXDateTime

    assert StoneXDateTime is not None
