import asyncio
import json
from decimal import Decimal
from typing import cast

import pytest
import respx
from pydantic import Field, ValidationError

from stonepy import AsyncStoneXClient, ClientConfig, StoneXClient
from stonepy._core.models import RequestModel, ResponseModel
from stonepy.models import SaveWatchlistRequestDTO


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


def _watchlist_request() -> SaveWatchlistRequestDTO:
    return SaveWatchlistRequestDTO.model_validate(
        {"ClientAccountId": 1, "Watchlist": {"Items": [{"MarketId": 7}]}}
    )


def test_request_assignment_rejects_wrong_type_and_preserves_value() -> None:
    request = _watchlist_request()
    with pytest.raises(ValidationError, match="client_account_id"):
        request.client_account_id = "invalid"  # type: ignore[assignment]
    assert request.client_account_id == 1


@pytest.mark.parametrize("asynchronous", [False, True])
@respx.mock
def test_valid_request_assignment_is_sent_on_wire(asynchronous: bool) -> None:
    request = _watchlist_request()
    request.client_account_id = 2
    # Previously unset fields must also be included by exclude_unset serialization.
    request.watchlist.watchlist_description = "updated"
    route = respx.post("https://api.example/v2/watchlists/save").respond(
        200, json={"WatchlistId": 1}
    )
    config = ClientConfig(base_url="https://api.example")

    async def run() -> None:
        async with AsyncStoneXClient(config) as client:
            await client.watchlist.save_watchlist(request)

    if asynchronous:
        asyncio.run(run())
    else:
        with StoneXClient(config) as client:
            client.watchlist.save_watchlist(request)

    assert json.loads(route.calls[0].request.content) == {
        "ClientAccountId": 2,
        "Watchlist": {"Items": [{"MarketId": 7}], "WatchlistDescription": "updated"},
    }


def test_nested_request_variant_validates_its_own_assignment() -> None:
    request = _watchlist_request()
    assert request.watchlist.items is not None
    with pytest.raises(ValidationError, match="market_id"):
        request.watchlist.items[0].market_id = "invalid"  # type: ignore[assignment]
    assert request.watchlist.items[0].market_id == 7


def test_nested_list_in_place_mutation_is_unguarded() -> None:
    request = _watchlist_request()
    assert request.watchlist.items is not None
    # Assignment validation cannot intercept list.append; A13 remains partially open.
    request.watchlist.items.append("invalid")  # type: ignore[arg-type]
    assert cast(object, request.watchlist.items[-1]) == "invalid"


def test_parent_does_not_validate_assignment_on_unvalidated_nested_model() -> None:
    class ExtensionRequest(RequestModel):
        nested: _Resp

    request = ExtensionRequest(nested=_Resp(OrderId=5))
    # The parent sees no assignment, and ResponseModel does not validate assignments itself.
    request.nested.order_id = "invalid"  # type: ignore[assignment]
    assert cast(object, request.nested.order_id) == "invalid"


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


def test_stonex_datetime_reexported_from_models() -> None:
    from stonepy._core.models import StoneXDateTime

    assert StoneXDateTime is not None
